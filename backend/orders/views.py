from django.db.models import Prefetch, Q
from django.http import FileResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Address, User
from catalog.models import Product, Category
from catalog.models import Coupon, ProductVariant
from core.pdf import invoice_pdf
from core.permissions import IsStaffRole, IsVendorOrOwner
from core.whatsapp import order_whatsapp_message, whatsapp_link
from orders.models import Cart, CartItem, Order
from orders.serializers import (
    AdminOrderCreateSerializer,
    CartItemSerializer,
    CartItemWriteSerializer,
    CartSerializer,
    CheckoutSerializer,
    CouponApplySerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)
from orders.services import (
    cancel_by_client,
    change_status,
    create_order,
    log_status,
    user_cart,
)
from payments.serializers import PaymentCreateSerializer, PaymentSerializer
from payments.services import record_payment

ORDER_RELATED = (
    "items__variant__product__images",
    "items__variant__product__variants",
    "payments",
    "delivery",
    "status_history__user",
)


def order_queryset():
    return Order.objects.select_related("user", "address", "delivery").prefetch_related(*ORDER_RELATED)


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=CartSerializer)
    def get(self, request):
        cart = user_cart(request.user)
        cart = Cart.objects.prefetch_related(
            "items__variant__product__images", "items__variant__product__variants"
        ).get(pk=cart.pk)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartItemsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CartItemWriteSerializer, responses=CartSerializer)
    def post(self, request):
        serializer = CartItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = ProductVariant.objects.filter(
            pk=serializer.validated_data["variant"], is_active=True
        ).select_related("product").first()
        if not variant or variant.product.status != "published":
            return Response({"detail": "Article introuvable."}, status=404)
        quantity = serializer.validated_data["quantity"]
        cart = user_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant, defaults={"quantity": 0}
        )
        new_quantity = (0 if created else item.quantity) + quantity
        if new_quantity > variant.stock_qty:
            return Response(
                {"detail": f"Stock insuffisant : {variant.stock_qty} disponible(s)."},
                status=400,
            )
        item.quantity = new_quantity
        item.save()
        cart = Cart.objects.prefetch_related(
            "items__variant__product__images"
        ).get(pk=cart.pk)
        return Response(CartSerializer(cart, context={"request": request}).data, status=201)


class CartItemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        item = CartItem.objects.filter(pk=pk, cart__user=request.user).select_related("variant").first()
        if not item:
            return Response({"detail": "Article introuvable dans votre panier."}, status=404)
        quantity = int(request.data.get("quantity", item.quantity))
        if quantity <= 0:
            item.delete()
        else:
            if quantity > item.variant.stock_qty:
                return Response(
                    {"detail": f"Stock insuffisant : {item.variant.stock_qty} disponible(s)."},
                    status=400,
                )
            item.quantity = quantity
            item.save(update_fields=["quantity"])
        cart = Cart.objects.prefetch_related("items__variant__product__images").get(
            pk=item.cart_id
        )
        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request, pk):
        CartItem.objects.filter(pk=pk, cart__user=request.user).delete()
        cart = user_cart(request.user)
        cart = Cart.objects.prefetch_related("items__variant__product__images").get(pk=cart.pk)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartCouponView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CouponApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = user_cart(request.user)
        coupon = Coupon.objects.filter(code=serializer.validated_data["code"].strip().upper()).first()
        if not coupon:
            return Response({"detail": "Code promo inconnu."}, status=400)
        try:
            coupon.validate_for(cart.subtotal)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        cart.coupon = coupon
        cart.save(update_fields=["coupon", "updated_at"])
        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        cart = user_cart(request.user)
        cart.coupon = None
        cart.save(update_fields=["coupon", "updated_at"])
        return Response(CartSerializer(cart, context={"request": request}).data)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderDetailSerializer
        return OrderListSerializer

    def get_queryset(self):
        qs = order_queryset()
        if self.request.user.is_staff_role:
            return qs
        return qs.filter(user=self.request.user)

    def get_serializer_context(self):
        return {"request": self.request, "include_margin": self.request.user.is_staff_role}

    @extend_schema(request=CheckoutSerializer, responses={201: OrderDetailSerializer})
    def create(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = user_cart(request.user)
        explicit_items = data.get("items")
        if explicit_items:
            items = explicit_items
            source_cart = None
        else:
            items = [
                {"variant": item.variant_id, "quantity": item.quantity}
                for item in cart.items.all()
            ]
            source_cart = cart
            if not items:
                return Response(
                    {"detail": "Votre panier est vide. Ajoutez un article pour commander."},
                    status=400,
                )

        address = None
        if data.get("fulfillment") == Order.Fulfillment.DELIVERY and data.get("address"):
            address = Address.objects.filter(pk=data["address"], user=request.user).first()
            if not address:
                return Response({"detail": "Adresse de livraison introuvable."}, status=400)

        order, created = create_order(
            user=request.user,
            items=items,
            fulfillment=data.get("fulfillment", Order.Fulfillment.DELIVERY),
            address=address,
            address_data=data.get("address_data"),
            channel=Order.Channel.APP,
            payment_method=data.get("payment_method", "cash"),
            payment_reference=data.get("payment_reference", ""),
            payment_amount=data.get("payment_amount"),
            note=data.get("note", ""),
            coupon_code=data.get("coupon_code", "") or (cart.coupon.code if source_cart and cart.coupon else ""),
            client_reference=data.get("client_reference"),
            delivery_slot=data.get("delivery_slot", ""),
            desired_date=data.get("desired_date"),
            source_cart=source_cart,
        )
        order = order_queryset().get(pk=order.pk)
        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=201 if created else 200,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        order = cancel_by_client(order, request.user, request.data.get("reason", ""))
        return Response(
            OrderDetailSerializer(
                order_queryset().get(pk=order.pk), context={"request": request}
            ).data
        )

    @action(detail=True, methods=["get"])
    def whatsapp(self, request, pk=None):
        order = self.get_object()
        from core.models import ShopSetting

        message = request.query_params.get("message") or order_whatsapp_message(order)
        return Response(
            {"url": whatsapp_link(ShopSetting.load().whatsapp_phone, message), "message": message}
        )

    @action(detail=True, methods=["get", "post"], url_path="payments")
    def payments(self, request, pk=None):
        order = self.get_object()
        if request.method == "GET":
            return Response(
                PaymentSerializer(order.payments.all(), many=True, context={"request": request}).data
            )
        if order.status in {Order.Status.CANCELLED, Order.Status.RETURNED}:
            return Response({"detail": "Cette commande est clôturée."}, status=400)
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["method"] != "orange_money":
            return Response(
                {"detail": "Seul Orange Money peut être déclaré depuis l'application client."},
                status=400,
            )
        payment = record_payment(
            order,
            method=serializer.validated_data["method"],
            amount=serializer.validated_data["amount"],
            user=request.user,
            om_reference=serializer.validated_data.get("om_reference"),
            payer_phone=serializer.validated_data.get("payer_phone", request.user.phone),
            screenshot=serializer.validated_data.get("screenshot"),
            note=serializer.validated_data.get("note", ""),
            auto_confirm=False,
        )
        return Response(
            PaymentSerializer(payment, context={"request": request}).data, status=201
        )

    @action(detail=True, methods=["get"])
    def invoice(self, request, pk=None):
        order = self.get_object()
        kind = request.query_params.get("kind", "invoice")
        if kind not in {"invoice", "receipt", "ticket", "delivery"}:
            return Response({"detail": "Type de document inconnu."}, status=400)
        if order.user_id and order.user_id != request.user.id and not request.user.is_staff_role:
            return Response({"detail": "Accès refusé."}, status=403)
        if kind == "receipt" and order.amount_paid <= 0:
            return Response(
                {"detail": "Aucun encaissement à justifier pour cette commande."}, status=400
            )
        pdf = invoice_pdf(order, kind=kind)
        suffix = {
            "invoice": "facture", "receipt": "recu", "ticket": "ticket", "delivery": "bon-livraison"
        }[kind]
        return FileResponse(
            pdf,
            as_attachment=False,
            filename=f"{suffix}-{order.number}.pdf",
            content_type="application/pdf",
        )


class AdminOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsVendorOrOwner]

    def get_serializer_class(self):
        if self.action in {"list"}:
            return OrderListSerializer
        if self.action == "create":
            return AdminOrderCreateSerializer
        return OrderDetailSerializer

    def get_queryset(self):
        qs = order_queryset()
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status__in=params["status"].split(","))
        if params.get("channel"):
            qs = qs.filter(channel=params["channel"])
        if params.get("payment_method"):
            qs = qs.filter(payments__method=params["payment_method"]).distinct()
        if params.get("payment_status") == "unpaid":
            qs = qs.filter(amount_paid=0)
        elif params.get("payment_status") == "partial":
            qs = qs.filter(amount_paid__gt=0, balance_due__gt=0)
        elif params.get("payment_status") == "paid":
            qs = qs.filter(balance_due=0)
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        if params.get("search"):
            search = params["search"]
            from django.db.models import Q

            qs = qs.filter(
                Q(number__icontains=search)
                | Q(customer_phone__icontains=search)
                | Q(customer_name__icontains=search)
            )
        return qs

    def get_serializer_context(self):
        return {"request": self.request, "include_margin": True}

    @extend_schema(request=AdminOrderCreateSerializer)
    def create(self, request):
        serializer = AdminOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        customer = None
        customer_id = data.get("user") or data.get("customer")
        if customer_id:
            customer = User.objects.filter(pk=customer_id).first()

        address = None
        if data.get("address"):
            address = Address.objects.filter(pk=data["address"]).first()

        order, created = create_order(
            user=customer,
            items=data["items"],
            fulfillment=data.get("fulfillment", Order.Fulfillment.DELIVERY),
            address=address,
            address_data=data.get("address_data"),
            channel=data.get("channel", Order.Channel.COUNTER),
            payment_method=data.get("payment_method", "cash"),
            payment_reference=data.get("payment_reference", ""),
            payment_amount=data.get("payment_amount"),
            note=data.get("note", ""),
            coupon_code=data.get("coupon_code", ""),
            client_reference=data.get("client_reference"),
            delivery_slot=data.get("delivery_slot", ""),
            desired_date=data.get("desired_date"),
            created_by=request.user,
            customer_name=data.get("customer_name", ""),
            customer_phone=data.get("customer_phone", ""),
            mark_paid=data.get("mark_paid", False),
            clear_cart=False,
        )
        if data.get("internal_note"):
            order.internal_note = data["internal_note"]
            order.save(update_fields=["internal_note", "updated_at"])
        order = order_queryset().get(pk=order.pk)
        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=201 if created else 200,
        )

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        if new_status not in dict(Order.Status.choices):
            return Response({"detail": "Statut inconnu."}, status=400)
        if new_status in {Order.Status.PREPARING, Order.Status.SHIPPING}:
            pending = order.payments.filter(status="pending").exists()
            if pending:
                return Response(
                    {
                        "detail": (
                            "Un paiement est encore à vérifier. Confirmez la réception réelle "
                            "du paiement avant de préparer la commande."
                        )
                    },
                    status=400,
                )
            if order.status == Order.Status.PENDING_PAYMENT:
                return Response(
                    {"detail": "La commande est en attente de paiement : confirmez d'abord le paiement."},
                    status=400,
                )
        order = change_status(
            order, new_status, user=request.user, reason=request.data.get("reason", "")
        )
        return Response(
            OrderDetailSerializer(
                order_queryset().get(pk=order.pk),
                context={"request": request, "include_margin": True},
            ).data
        )

    @action(detail=True, methods=["get"], url_path="invoice")
    def invoice(self, request, pk=None):
        order = self.get_object()
        kind = request.query_params.get("kind", "invoice")
        if kind not in {"invoice", "receipt", "ticket", "delivery"}:
            return Response({"detail": "Type de document inconnu."}, status=400)
        if kind == "receipt" and order.amount_paid <= 0:
            return Response(
                {"detail": "Aucun encaissement à justifier pour cette commande."}, status=400
            )
        pdf = invoice_pdf(order, kind=kind)
        suffix = {
            "invoice": "facture", "receipt": "recu", "ticket": "ticket", "delivery": "bon-livraison"
        }[kind]
        return FileResponse(
            pdf, as_attachment=False, filename=f"{suffix}-{order.number}.pdf",
            content_type="application/pdf",
        )

    @action(detail=False, methods=["get"])
    def home(self, request):
        """Données de l'écran d'accueil : bannières, catégories, produits en vedette."""
        from django.db.models import Count, When, Value, CharField
        from catalog.models import Product, Category
        
        # Bannières (images de démonstration)
        banners = [
            {"image": "https://images.unsplash.com/photo-1556421866-2a45f1487052?w=800&h=400&fit=crop", "title": "Nouvelle collection de tapis de gym"},
            {"image": "https://images.unsplash.com/photo-1567219715032-cb0489d4952e?w=800&h=400&fit=crop", "title": "Offres spéciales sur les poids"},
        ]
        
        # Catégories avec compte de produits
        categories = Category.objects.annotate(
            product_count=Count('products', filter=Q(products__status='published'))
        ).filter(product_count__gt=0)[:5]
        categories_data =[
            {"id": c.id, "name": c.name}
            for c in categories
        ]
        
        # Produits populaires (les plus vendus) - sans serializer, construction manuelle
        popular = Product.objects.filter(status='published').order_by('-sold_count')[:8]
        popular_data = [
            {"id": p.id, "name": p.name, "price": p.price, "imageUrl": p.primary_image, "slug": p.slug}
            for p in popular
        ]
        
        # Nouveautés
        new_arrivals = Product.objects.filter(status='published', is_new=True)[:8]
        new_data = [
            {"id": p.id, "name": p.name, "price": p.price, "imageUrl": p.primary_image, "slug": p.slug}
            for p in new_arrivals
        ]
        
        # Promotions
        promotions = Product.objects.filter(status='published').order_by('?')[:8]
        promo_data = [
            {"id": p.id, "name": p.name, "price": p.price, "imageUrl": p.primary_image, "slug": p.slug}
            for p in promotions
        ]
        
        return Response({
            "banners": banners,
            "categories": categories_data,
            "popular": popular_data,
            "new_arrivals": new_data,
            "promotions": promo_data,
        })

    def receipts(self, request):
        """Liste tous les reçus/factures avec filtrage."""
        params = request.query_params
        qs = order_queryset()

        # Filtrage par client (phone ou name)
        search = params.get("search")
        if search:
            qs = qs.filter(
                Q(customer_phone__icontains=search)
                | Q(customer_name__icontains=search)
            )

        # Filtrage par date
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # Filtrage par statut de paiement
        payment_status = params.get("payment_status")
        if payment_status == "unpaid":
            qs = qs.filter(amount_paid=0)
        elif payment_status == "partial":
            qs = qs.filter(amount_paid__gt=0, balance_due__gt=0)
        elif payment_status == "paid":
            qs = qs.filter(balance_due=0)

        # Filtrage par type de document (receipt vs invoice)
        kind = params.get("kind")
        if kind == "receipt":
            qs = qs.filter(amount_paid__gt=0)

        # Pagination et tri
        qs = qs.order_by("-created_at")

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = OrderListSerializer(
                page, many=True, context={"request": request, "include_margin": True}
            )
            return self.get_paginated_response(serializer.data)

        serializer = OrderListSerializer(qs, many=True, context={"request": request, "include_margin": True})
        return Response(serializer.data)


    @action(detail=True, methods=["get"])
    def whatsapp(self, request, pk=None):
        order = self.get_object()
        message = request.query_params.get("message") or (
            f"Bonjour {order.customer_name}, c'est Konaté Service Gym au sujet de "
            f"votre commande {order.number}."
        )
        return Response({"url": whatsapp_link(order.customer_phone, message), "message": message})

    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        order = self.get_object()
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = record_payment(
            order,
            method=serializer.validated_data["method"],
            amount=serializer.validated_data["amount"],
            user=request.user,
            om_reference=serializer.validated_data.get("om_reference"),
            payer_phone=serializer.validated_data.get("payer_phone", order.customer_phone),
            screenshot=serializer.validated_data.get("screenshot"),
            note=serializer.validated_data.get("note", ""),
            auto_confirm=bool(request.data.get("auto_confirm", False)),
        )
        return Response(PaymentSerializer(payment, context={"request": request}).data, status=201)

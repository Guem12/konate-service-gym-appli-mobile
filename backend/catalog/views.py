from django.db.models import Count, Min, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from catalog.models import (
    Brand,
    Category,
    Coupon,
    Favorite,
    Product,
    Promotion,
)
from catalog.serializers import (
    AdminProductSerializer,
    BrandSerializer,
    CategorySerializer,
    CouponSerializer,
    FavoriteSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    PromotionSerializer,
)
from core.permissions import IsVendorOrOwner


def published_products():
    return (
        Product.objects.filter(status=Product.Status.PUBLISHED)
        .select_related("brand", "category")
        .prefetch_related("variants", "images", "promotions")
    )


class CatalogContextMixin:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        request = self.request
        if request.user.is_authenticated:
            context["favorite_ids"] = set(
                Favorite.objects.filter(user=request.user).values_list("product_id", flat=True)
            )
        return context


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True, parent__isnull=True)
            .prefetch_related("children__children")
            .annotate(published_count=Count("products", filter=Q(products__status=Product.Status.PUBLISHED)))
        )


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BrandSerializer
    lookup_field = "slug"
    pagination_class = None
    queryset = Brand.objects.all()


class ProductViewSet(CatalogContextMixin, viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"

    def get_object(self):
        """Accepte /products/<slug> et /products/<id> (utilisé par l'application)."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup = self.kwargs.get(self.lookup_field, "")
        if str(lookup).isdigit():
            obj = get_object_or_404(queryset, pk=lookup)
        else:
            obj = get_object_or_404(queryset, slug=lookup)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer

    def get_queryset(self):
        qs = published_products().annotate(min_variant_price=Min("variants__price_sale"))
        params = self.request.query_params

        category = params.get("category")
        if category:
            if str(category).isdigit():
                category_obj = Category.objects.filter(pk=category).first()
            else:
                category_obj = Category.objects.filter(slug=category).first()
            if category_obj:
                ids = [category_obj.pk] + list(
                    category_obj.children.values_list("pk", flat=True)
                )
                qs = qs.filter(category_id__in=ids)

        brand = params.get("brand")
        if brand:
            qs = qs.filter(Q(brand__slug=brand) | Q(brand__id=brand if str(brand).isdigit() else None))

        min_price = params.get("price_min")
        max_price = params.get("price_max")
        if min_price:
            qs = qs.filter(min_variant_price__gte=min_price)
        if max_price:
            qs = qs.filter(min_variant_price__lte=max_price)

        availability = params.get("availability")
        if availability == "in_stock":
            qs = qs.filter(variants__stock_qty__gt=0, variants__is_active=True).distinct()
        elif availability == "out_of_stock":
            qs = qs.exclude(variants__stock_qty__gt=0, variants__is_active=True)

        if params.get("featured") in {"1", "true", "True"}:
            qs = qs.filter(is_featured=True)
        if params.get("promotion") in {"1", "true", "True"}:
            now = timezone.now()
            qs = qs.filter(
                promotions__is_active=True, promotions__start_at__lte=now, promotions__end_at__gte=now
            ).distinct()

        search = params.get("search") or params.get("q")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(brand__name__icontains=search)
                | Q(category__name__icontains=search)
                | Q(description__icontains=search)
            )

        ordering = params.get("ordering", "-created_at")
        allowed = {
            "price", "-price", "created_at", "-created_at", "sold_count", "-sold_count", "name", "-name",
        }
        if ordering == "price":
            return qs.order_by("min_variant_price")
        if ordering == "-price":
            return qs.order_by("-min_variant_price")
        if ordering in allowed:
            return qs.order_by(ordering)
        return qs.order_by("-created_at")

    @extend_schema(
        parameters=[OpenApiParameter("q", str, description="Texte recherché")],
        responses={200: dict},
    )
    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def search(self, request):
        query = (request.query_params.get("q") or "").strip()
        qs = published_products()
        if query:
            qs = qs.filter(
                Q(name__icontains=query) | Q(brand__name__icontains=query)
                | Q(category__name__icontains=query)
            )
        results = []
        for product in qs[:8]:
            serializer = ProductListSerializer(product, context={"request": request})
            results.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug,
                    "price": serializer.data["price"],
                    "image": serializer.data["primary_image"],
                }
            )
        return Response({"results": results})


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("product")
            .prefetch_related("product__variants", "product__images")
        )

    @action(detail=False, methods=["post"])
    def toggle(self, request):
        product_id = request.data.get("product")
        favorite = Favorite.objects.filter(user=request.user, product_id=product_id).first()
        if favorite:
            favorite.delete()
            return Response({"is_favorite": False})
        product = Product.objects.filter(pk=product_id, status=Product.Status.PUBLISHED).first()
        if not product:
            return Response({"detail": "Produit introuvable."}, status=404)
        Favorite.objects.create(user=request.user, product=product)
        return Response({"is_favorite": True}, status=201)


class HomeView(viewsets.ViewSet):
    """Contenu de l'accueil : bannières, catégories, populaires, nouveautés."""

    permission_classes = [permissions.AllowAny]

    def list(self, request):
        now = timezone.now()
        promotions = Promotion.objects.filter(
            is_active=True, start_at__lte=now, end_at__gte=now
        ).prefetch_related("products").order_by("-show_on_home", "-start_at")
        banners = [p for p in promotions if p.show_on_home][:5]
        categories = Category.objects.filter(is_active=True, parent__isnull=True).annotate(
            published_count=Count("products", filter=Q(products__status=Product.Status.PUBLISHED))
        )
        base = published_products()
        context = {"request": request}
        if request.user.is_authenticated:
            context["favorite_ids"] = set(
                Favorite.objects.filter(user=request.user).values_list("product_id", flat=True)
            )
        return Response(
            {
                "banners": PromotionSerializer(banners, many=True, context=context).data,
                "categories": CategorySerializer(categories, many=True, context=context).data,
                "popular": ProductListSerializer(
                    base.order_by("-sold_count")[:8], many=True, context=context
                ).data,
                "new": ProductListSerializer(
                    base.filter(is_new=True).order_by("-created_at")[:8], many=True, context=context
                ).data,
                "promotions": ProductListSerializer(
                    base.filter(
                        promotions__is_active=True, promotions__start_at__lte=now,
                        promotions__end_at__gte=now,
                    ).distinct()[:8],
                    many=True,
                    context=context,
                ).data,
                "featured": ProductListSerializer(
                    base.filter(is_featured=True)[:8], many=True, context=context
                ).data,
            }
        )


# --- Administration ---------------------------------------------------------
class AdminProductViewSet(viewsets.ModelViewSet):
    serializer_class = AdminProductSerializer
    permission_classes = [IsVendorOrOwner]
    search_fields = ["name", "variants__sku", "variants__barcode", "brand__name"]
    filterset_fields = ["status", "category", "brand", "is_featured"]
    ordering_fields = ["created_at", "name", "is_featured"]

    def get_queryset(self):
        return (
            Product.objects.all()
            .select_related("brand", "category")
            .prefetch_related("variants", "images")
            .distinct()
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        before = {
            v.pk: v.price_sale for v in instance.variants.all()
        }
        product = serializer.save()
        from accounts.services import log_action

        for variant in product.variants.all():
            if before.get(variant.pk) not in (None, variant.price_sale):
                log_action(
                    self.request.user, "product_price_change", "variant", variant.pk,
                    f"{product.name} ({variant.label}) : {before[variant.pk]} → {variant.price_sale} FCFA",
                )

    def perform_destroy(self, instance):
        from accounts.services import log_action

        log_action(self.request.user, "product_delete", "product", instance.pk, instance.name)
        instance.status = Product.Status.HIDDEN
        instance.save(update_fields=["status"])

    @action(detail=True, methods=["post"], permission_classes=[IsVendorOrOwner])
    def duplicate(self, request, pk=None):
        product = self.get_object()
        variants = list(product.variants.all())
        product.pk = None
        product.slug = ""
        product.name = f"{product.name} (copie)"
        product.status = Product.Status.DRAFT
        product.save()
        for variant in variants:
            variant.pk = None
            variant.product = product
            variant.sku = f"{variant.sku}-COPIE"
            variant.save()
        return Response(AdminProductSerializer(product, context={"request": request}).data, status=201)


class AdminCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsVendorOrOwner]
    queryset = Category.objects.all().order_by("order", "name")
    pagination_class = None


class AdminBrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    permission_classes = [IsVendorOrOwner]
    queryset = Brand.objects.all()
    pagination_class = None


class AdminPromotionViewSet(viewsets.ModelViewSet):
    serializer_class = PromotionSerializer
    permission_classes = [IsVendorOrOwner]
    queryset = Promotion.objects.all().prefetch_related("products")
    pagination_class = None


class AdminCouponViewSet(viewsets.ModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [IsVendorOrOwner]
    queryset = Coupon.objects.all()
    search_fields = ["code"]
    pagination_class = None

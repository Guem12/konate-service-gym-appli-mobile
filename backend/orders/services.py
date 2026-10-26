"""Cœur métier des commandes : création transactionnelle, stock, statuts."""
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import Address
from catalog.models import Coupon, ProductVariant
from core.push import notify_order_status, send_push
from inventory.models import StockMovement
from inventory.services import record_movement
from orders.models import Cart, Order, OrderItem, OrderStatusHistory

ALLOWED_TRANSITIONS = {
    Order.Status.PENDING_PAYMENT: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {
        Order.Status.PREPARING, Order.Status.SHIPPING, Order.Status.DELIVERED, Order.Status.CANCELLED
    },
    Order.Status.PREPARING: {
        Order.Status.SHIPPING, Order.Status.DELIVERED, Order.Status.CANCELLED
    },
    Order.Status.SHIPPING: {Order.Status.DELIVERED, Order.Status.CANCELLED},
    Order.Status.DELIVERED: {Order.Status.RETURNED},
    Order.Status.CANCELLED: set(),
    Order.Status.RETURNED: set(),
}


def log_status(order, status, user=None, note=""):
    return OrderStatusHistory.objects.create(
        order=order, status=status, user=user, note=note[:200]
    )


def restock_order(order, user=None, reason="Retour en stock", movement_type=StockMovement.Type.RETURN):
    if order.stock_restocked:
        return
    for item in order.items.all():
        record_movement(
            variant_id=item.variant_id,
            quantity=item.quantity,
            movement_type=movement_type,
            user=user,
            reason=f"{reason} — {order.number}",
            order=order,
        )
    order.stock_restocked = True
    order.save(update_fields=["stock_restocked", "updated_at"])


def change_status(order, new_status, user=None, reason="", by_client=False):
    """Change le statut d'une commande en respectant le cycle de vie."""
    if new_status == order.status:
        return order
    if by_client:
        if not order.can_cancel or new_status != Order.Status.CANCELLED:
            raise ValidationError(
                {"detail": "Cette commande ne peut plus être annulée. Contactez la boutique."}
            )
    if new_status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise ValidationError(
            {
                "detail": (
                    f"Passage impossible de « {order.get_status_display()} » "
                    f"à « {dict(Order.Status.choices)[new_status]} »."
                )
            }
        )

    now = timezone.now()
    update_fields = ["status", "updated_at"]
    order.status = new_status

    if new_status == Order.Status.CONFIRMED:
        order.confirmed_at = now
        update_fields.append("confirmed_at")
    elif new_status == Order.Status.PREPARING:
        order.preparing_at = now
        update_fields.append("preparing_at")
    elif new_status == Order.Status.SHIPPING:
        order.shipped_at = now
        update_fields.append("shipped_at")
    elif new_status == Order.Status.DELIVERED:
        order.delivered_at = now
        update_fields.append("delivered_at")
    elif new_status == Order.Status.CANCELLED:
        order.cancelled_at = now
        order.cancel_reason = reason[:200]
        update_fields += ["cancelled_at", "cancel_reason"]
    elif new_status == Order.Status.RETURNED:
        order.returned_at = now
        update_fields.append("returned_at")

    order.save(update_fields=update_fields)

    if new_status in {Order.Status.CANCELLED, Order.Status.RETURNED}:
        restock_order(
            order, user=user,
            reason=reason or f"Commande {order.get_status_display().lower()}",
        )
    if new_status == Order.Status.DELIVERED:
        from catalog.models import Product

        for item in order.items.all():
            Product.objects.filter(pk=item.variant.product_id).update(
                sold_count=F("sold_count") + item.quantity
            )
        from deliveries.models import Delivery

        Delivery.objects.filter(order=order).update(status="delivered", delivered_at=now)
    if new_status == Order.Status.SHIPPING:
        from deliveries.models import Delivery

        Delivery.objects.filter(order=order).update(status="in_transit")
    if new_status == Order.Status.PREPARING:
        from deliveries.models import Delivery

        Delivery.objects.filter(order=order, status="to_prepare").update(status="to_prepare")

    log_status(order, new_status, user=user, note=reason)
    notify_order_status(order)
    return order


def _normalize_items(items):
    merged = {}
    for item in items or []:
        try:
            variant_id = int(item.get("variant") or item.get("variant_id"))
            quantity = int(item.get("quantity", 1))
        except (TypeError, ValueError, AttributeError):
            raise ValidationError({"items": "Chaque ligne doit contenir une variante et une quantité."})
        if quantity <= 0:
            raise ValidationError({"items": "La quantité doit être supérieure à zéro."})
        merged[variant_id] = merged.get(variant_id, 0) + quantity
    if not merged:
        raise ValidationError({"items": "Votre panier est vide."})
    return merged


@transaction.atomic
def create_order(
    *,
    user,
    items,
    fulfillment=Order.Fulfillment.DELIVERY,
    address=None,
    address_data=None,
    channel=Order.Channel.APP,
    payment_method="cash",
    payment_reference="",
    payment_amount=None,
    note="",
    coupon_code="",
    client_reference=None,
    delivery_slot="",
    desired_date=None,
    created_by=None,
    customer_name="",
    customer_phone="",
    mark_paid=False,
    clear_cart=True,
    source_cart=None,
):
    """Crée une commande en une transaction, avec verrouillage du stock.

    Retourne (order, created). Une même `client_reference` renvoie la commande
    existante : aucune commande n'est perdue ni dupliquée sur une connexion
    instable.
    """
    from payments.models import Payment

    if client_reference:
        existing = Order.objects.filter(client_reference=client_reference).first()
        if existing:
            return existing, False

    requested = _normalize_items(items)

    variants = {
        v.pk: v
        for v in ProductVariant.objects.select_for_update()
        .select_related("product")
        .filter(pk__in=sorted(requested.keys()))
    }
    if len(variants) != len(requested):
        raise ValidationError({"items": "Un article de votre panier n'est plus disponible."})

    subtotal = 0
    for variant_id, quantity in requested.items():
        variant = variants[variant_id]
        if not variant.is_active or variant.product.status != "published":
            raise ValidationError(
                {"items": f"« {variant.product.name} » n'est plus en vente."}
            )
        if variant.stock_qty < quantity:
            raise ValidationError(
                {
                    "items": (
                        f"Stock insuffisant pour « {variant.product.name} — {variant.label} » : "
                        f"{variant.stock_qty} disponible(s), {quantity} demandé(s)."
                    )
                }
            )
        subtotal += variant.price_sale * quantity

    coupon = None
    discount = 0
    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code.strip().upper()).first()
        if not coupon:
            raise ValidationError({"coupon_code": "Code promo inconnu."})
        try:
            discount = coupon.validate_for(subtotal)
        except ValueError as exc:
            raise ValidationError({"coupon_code": str(exc)})

    if address is not None and user and address.user_id != user.id and not created_by:
        raise ValidationError({"address": "Adresse inconnue."})

    order = Order(
        user=user,
        customer_name=(customer_name or (user.full_name if user else ""))[:120],
        customer_phone=(customer_phone or (user.phone if user else ""))[:20],
        channel=channel,
        fulfillment=fulfillment,
        subtotal=subtotal,
        discount=discount,
        total=max(0, subtotal - discount),
        delivery_fee=0,
        coupon=coupon,
        coupon_code=coupon.code if coupon else "",
        note=note,
        client_reference=client_reference or None,
        created_by=created_by,
        delivery_slot=delivery_slot,
        desired_date=desired_date,
    )

    if fulfillment == Order.Fulfillment.DELIVERY:
        if address is None and address_data:
            order.delivery_district = (address_data.get("district") or "")[:80]
            order.delivery_street = (address_data.get("street") or "")[:160]
            order.delivery_landmark = (address_data.get("landmark") or "")[:160]
            order.delivery_phone = (address_data.get("phone") or order.customer_phone)[:20]
        elif address is not None:
            order.address = address
            order.delivery_district = address.district[:80]
            order.delivery_street = address.street[:160]
            order.delivery_landmark = address.landmark[:160]
            order.delivery_phone = (address.phone or order.customer_phone)[:20]
        elif channel == Order.Channel.APP:
            raise ValidationError({"address": "Choisissez une adresse de livraison."})
        else:
            order.delivery_district = "À confirmer"
            order.delivery_phone = order.customer_phone

    order.save()
    log_status(order, Order.Status.PENDING_PAYMENT, user=created_by or user, note="Commande créée")

    for variant_id, quantity in requested.items():
        variant = variants[variant_id]
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name,
            variant_label=variant.label,
            sku=variant.sku,
            quantity=quantity,
            unit_price_sale=variant.price_sale,
            unit_price_purchase=variant.price_purchase,
        )
        record_movement(
            variant_id=variant.pk,
            quantity=-quantity,
            movement_type=StockMovement.Type.SALE,
            user=created_by or user,
            reason=f"Commande {order.number}",
            order=order,
        )

    if fulfillment == Order.Fulfillment.DELIVERY:
        from deliveries.models import Delivery

        Delivery.objects.create(
            order=order,
            courier_name="",
            slot=delivery_slot,
            status="to_prepare",
            address_text=order.delivery_address_text,
        )

    if payment_method == "orange_money":
        if not payment_reference:
            raise ValidationError(
                {"payment_reference": "Saisissez la référence de la transaction Orange Money."}
            )
        try:
            Payment.objects.create(
                order=order,
                method=Payment.Method.ORANGE_MONEY,
                amount=payment_amount or order.total,
                om_reference=payment_reference.strip().upper(),
                payer_phone=order.customer_phone,
                status=Payment.Status.PENDING,
                created_by=user,
            )
        except IntegrityError:
            raise ValidationError(
                {"payment_reference": "Cette référence Orange Money a déjà été utilisée."}
            )
        order.status = Order.Status.PENDING_PAYMENT
        order.save(update_fields=["status"])
    elif mark_paid:
        amount = payment_amount if payment_amount is not None else order.total
        Payment.objects.create(
            order=order,
            method=Payment.Method.CASH,
            amount=amount,
            status=Payment.Status.CONFIRMED,
            confirmed_at=timezone.now(),
            confirmed_by=created_by or user,
            created_by=created_by or user,
            note="Encaissé à la création de la commande",
        )
        order.amount_paid = min(amount, order.total)
        if order.amount_paid >= order.total:
            change_status(order, Order.Status.CONFIRMED, user=created_by or user, reason="Payée")
        order.save()
    elif payment_method == "cash":
        # Espèces à la livraison / au comptoir : commande acceptée, encaissement à venir.
        change_status(order, Order.Status.CONFIRMED, user=created_by or user, reason="Paiement à la livraison")

    if coupon:
        Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)

    if clear_cart and source_cart is not None:
        source_cart.items.all().delete()
        source_cart.coupon = None
        source_cart.save(update_fields=["coupon", "updated_at"])

    if order.user_id:
        send_push(
            order.user,
            "Commande enregistrée",
            f"Votre commande {order.number} d'un montant de {order.total:,} FCFA a bien été reçue.".replace(",", " "),
            order=order,
        )
    return order, True


def user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def cart_for_request(user):
    return (
        Cart.objects.filter(user=user)
        .prefetch_related(
            "items__variant__product__images", "items__variant__product__variants"
        )
        .first()
    )


def cancel_by_client(order, user, reason=""):
    if order.user_id != user.id:
        raise ValidationError({"detail": "Commande introuvable."})
    if not order.can_cancel:
        raise ValidationError(
            {"detail": "Cette commande ne peut plus être annulée. Contactez la boutique sur WhatsApp."}
        )
    return change_status(order, Order.Status.CANCELLED, user=user, reason=reason, by_client=True)

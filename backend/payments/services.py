from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.push import send_push
from orders.models import Order
from payments.models import Payment


def recalculate_payments(order):
    """Recalcule le montant payé et le solde à partir des paiements confirmés."""
    paid = (
        order.payments.filter(status=Payment.Status.CONFIRMED).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )
    order.amount_paid = min(paid, order.total)
    order.balance_due = max(0, order.total - paid)
    order.save(update_fields=["amount_paid", "balance_due", "updated_at"])
    return order


@transaction.atomic
def confirm_payment(payment, user):
    """Le propriétaire confirme la réception réelle du paiement."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == Payment.Status.CONFIRMED:
        return payment
    if payment.status == Payment.Status.REJECTED:
        raise ValidationError({"detail": "Ce paiement a été rejeté."})

    payment.status = Payment.Status.CONFIRMED
    payment.confirmed_at = timezone.now()
    payment.confirmed_by = user
    payment.save(update_fields=["status", "confirmed_at", "confirmed_by"])

    order = payment.order
    recalculate_payments(order)

    if order.status == Order.Status.PENDING_PAYMENT and order.amount_paid > 0:
        from orders.services import change_status

        change_status(
            order, Order.Status.CONFIRMED, user=user,
            reason=f"Paiement {payment.get_method_display()} confirmé",
        )
    if order.user_id:
        send_push(
            order.user,
            "Paiement confirmé",
            f"Votre paiement de {payment.amount:,} FCFA pour la commande {order.number} "
            f"a été confirmé.".replace(",", " "),
            order=order,
        )
    return payment


@transaction.atomic
def reject_payment(payment, user, reason=""):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == Payment.Status.CONFIRMED:
        raise ValidationError(
            {"detail": "Un paiement confirmé ne peut pas être rejeté sans intervention du propriétaire."}
        )
    payment.status = Payment.Status.REJECTED
    payment.rejected_reason = reason[:200]
    payment.confirmed_by = user
    payment.save(update_fields=["status", "rejected_reason", "confirmed_by"])
    recalculate_payments(payment.order)
    if payment.order.user_id:
        send_push(
            payment.order.user,
            "Paiement non vérifié",
            f"Le paiement de {payment.amount:,} FCFA pour la commande "
            f"{payment.order.number} n'a pas pu être vérifié. Contactez la boutique "
            f"sur WhatsApp.".replace(",", " "),
            order=payment.order,
        )
    return payment


@transaction.atomic
def record_payment(order, *, method, amount, user, om_reference=None, payer_phone="",
                   screenshot=None, note="", auto_confirm=False):
    if amount <= 0:
        raise ValidationError({"amount": "Le montant doit être supérieur à zéro."})
    if method == Payment.Method.ORANGE_MONEY and not om_reference:
        raise ValidationError(
            {"om_reference": "La référence de la transaction Orange Money est obligatoire."}
        )
    payment = Payment(
        order=order,
        method=method,
        amount=amount,
        om_reference=om_reference,
        payer_phone=payer_phone,
        screenshot=screenshot,
        note=note,
        created_by=user,
        status=Payment.Status.CONFIRMED if auto_confirm else Payment.Status.PENDING,
        confirmed_at=timezone.now() if auto_confirm else None,
        confirmed_by=user if auto_confirm else None,
    )
    payment.save()
    recalculate_payments(order)
    if auto_confirm and order.status == Order.Status.PENDING_PAYMENT:
        from orders.services import change_status

        change_status(order, Order.Status.CONFIRMED, user=user, reason="Paiement enregistré")
    return payment

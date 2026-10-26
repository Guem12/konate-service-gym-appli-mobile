from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsVendorOrOwner
from deliveries.models import Delivery
from deliveries.serializers import DeliverySerializer, DeliveryUpdateSerializer
from orders.models import Order
from orders.services import change_status, restock_order


class AdminDeliveryViewSet(viewsets.ModelViewSet):
    serializer_class = DeliverySerializer
    permission_classes = [IsVendorOrOwner]
    http_method_names = ["get", "patch", "head", "options"]
    filterset_fields = ["status", "courier_name"]
    search_fields = ["order__number", "order__customer_name", "order__customer_phone", "zone"]
    ordering_fields = ["created_at", "delivered_at"]

    def get_queryset(self):
        qs = Delivery.objects.select_related("order").all()
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(order__desired_date=date)
        return qs

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        delivery = self.get_object()
        serializer = DeliveryUpdateSerializer(delivery, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        previous_status = delivery.status
        serializer.save()
        delivery.refresh_from_db()
        order = delivery.order

        if delivery.status == Delivery.Status.DELIVERED:
            delivery.delivered_at = delivery.delivered_at or timezone.now()
            delivery.save(update_fields=["delivered_at", "updated_at"])
            if order.status != Order.Status.DELIVERED:
                change_status(order, Order.Status.DELIVERED, user=request.user, reason="Livraison remise")
            if delivery.amount_collected and not delivery.cash_reconciled:
                from payments.models import Payment

                Payment.objects.create(
                    order=order,
                    method=Payment.Method.CASH,
                    amount=min(delivery.amount_collected, order.balance_due or order.total),
                    status=Payment.Status.PENDING,
                    note="Encaissement à la livraison — à vérifier et reverser",
                    created_by=request.user,
                )
        elif delivery.status == Delivery.Status.FAILED:
            if delivery.failure_action == Delivery.FailureAction.RESTOCK:
                restock_order(order, user=request.user, reason="Échec de livraison")
                if order.status != Order.Status.CANCELLED:
                    change_status(
                        order, Order.Status.CANCELLED, user=request.user,
                        reason=delivery.failure_reason or "Échec de livraison",
                    )
            elif previous_status != Delivery.Status.FAILED:
                order.internal_note = (
                    f"{order.internal_note}\nÉchec de livraison : {delivery.failure_reason}".strip()
                )
                order.save(update_fields=["internal_note", "updated_at"])
        elif delivery.status in {Delivery.Status.IN_TRANSIT, Delivery.Status.TO_PREPARE}:
            if delivery.status == Delivery.Status.IN_TRANSIT and order.status in {
                Order.Status.CONFIRMED, Order.Status.PREPARING
            }:
                change_status(order, Order.Status.SHIPPING, user=request.user, reason="Livreur en route")

        return Response(DeliverySerializer(delivery).data)

    @action(detail=False, methods=["get"])
    def today(self, request):
        today = timezone.localdate()
        deliveries = self.get_queryset().filter(
            order__desired_date=today
        ) | self.get_queryset().filter(created_at__date=today)
        return Response(DeliverySerializer(deliveries.distinct(), many=True).data)

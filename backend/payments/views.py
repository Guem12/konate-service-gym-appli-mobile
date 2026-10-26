from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.services import log_action
from core.permissions import IsOwner
from payments.models import Payment
from payments.serializers import PaymentRejectSerializer, PaymentSerializer
from payments.services import confirm_payment, reject_payment


class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsOwner]
    filterset_fields = ["status", "method", "order"]
    search_fields = ["order__number", "om_reference", "payer_phone", "order__customer_name"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        return Payment.objects.select_related("order").all()

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        payment = self.get_object()
        payment = confirm_payment(payment, request.user)
        log_action(
            request.user, "payment_confirm", "payment", payment.pk,
            f"{payment.get_method_display()} {payment.amount} FCFA — {payment.order.number}",
        )
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        payment = self.get_object()
        serializer = PaymentRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = reject_payment(payment, request.user, serializer.validated_data.get("reason", ""))
        log_action(
            request.user, "payment_reject", "payment", payment.pk,
            f"{payment.amount} FCFA — {payment.order.number}",
        )
        return Response(PaymentSerializer(payment).data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        payments = self.get_queryset().filter(status=Payment.Status.PENDING)
        return Response(
            {
                "count": payments.count(),
                "total": payments.aggregate(total=Sum("amount"))["total"] or 0,
                "results": PaymentSerializer(payments, many=True).data,
            }
        )

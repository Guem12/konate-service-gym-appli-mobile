from rest_framework import serializers

from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_number = serializers.CharField(source="order.number", read_only=True)
    customer_name = serializers.CharField(source="order.customer_name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "order", "order_number", "customer_name", "method", "method_display",
            "amount", "status", "status_display", "om_reference", "payer_phone",
            "screenshot", "note", "confirmed_at", "rejected_reason", "created_at",
        ]
        read_only_fields = ["status", "confirmed_at", "rejected_reason", "created_at"]

    def validate_om_reference(self, value):
        if not value:
            return None
        normalized = value.strip().upper()
        existing = Payment.objects.filter(om_reference=normalized)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                "Cette référence Orange Money a déjà été utilisée sur une autre commande."
            )
        return normalized

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à zéro.")
        return value


class PaymentCreateSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=Payment.Method.choices, default=Payment.Method.ORANGE_MONEY)
    amount = serializers.IntegerField(min_value=1)
    om_reference = serializers.CharField(required=False, allow_blank=True, max_length=60)
    payer_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    note = serializers.CharField(required=False, allow_blank=True, max_length=200)
    screenshot = serializers.ImageField(required=False, allow_null=True)


class PaymentRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)

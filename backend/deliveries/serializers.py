from rest_framework import serializers

from deliveries.models import Delivery


class DeliverySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_number = serializers.CharField(source="order.number", read_only=True)
    customer_name = serializers.CharField(source="order.customer_name", read_only=True)
    customer_phone = serializers.CharField(source="order.customer_phone", read_only=True)
    total = serializers.IntegerField(source="order.total", read_only=True)
    balance_due = serializers.IntegerField(source="order.balance_due", read_only=True)
    district = serializers.CharField(source="order.delivery_district", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id", "order", "order_number", "customer_name", "customer_phone", "status",
            "status_display", "courier_name", "slot", "address_text", "zone", "district",
            "delivery_cost", "amount_collected", "cash_reconciled", "delivered_at",
            "failure_action", "failure_reason", "proof_note", "total", "balance_due",
            "created_at", "updated_at",
        ]
        read_only_fields = ["order", "created_at", "updated_at"]


class DeliveryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = [
            "status", "courier_name", "slot", "zone", "delivery_cost",
            "amount_collected", "cash_reconciled", "failure_action",
            "failure_reason", "proof_note",
        ]

    def validate_amount_collected(self, value):
        if value < 0:
            raise serializers.ValidationError("Le montant encaissé ne peut pas être négatif.")
        return value

from rest_framework import serializers

from inventory.models import StockMovement, Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id", "name", "contact_name", "phone", "address",
            "products_supplied", "notes", "is_active", "created_at",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    variant_label = serializers.CharField(source="variant.label", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    user_name = serializers.CharField(source="user.full_name", read_only=True, default="")

    class Meta:
        model = StockMovement
        fields = [
            "id", "variant", "product_name", "variant_label", "sku", "movement_type",
            "movement_type_display", "quantity", "stock_after", "reason", "user_name",
            "supplier", "order", "created_at",
        ]
        read_only_fields = ["stock_after", "order", "created_at"]


class StockAdjustmentSerializer(serializers.Serializer):
    variant = serializers.IntegerField()
    movement_type = serializers.ChoiceField(
        choices=[StockMovement.Type.IN, StockMovement.Type.BREAKAGE,
                 StockMovement.Type.RETURN, StockMovement.Type.ADJUSTMENT,
                 StockMovement.Type.RESTOCK]
    )
    quantity = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)
    supplier = serializers.IntegerField(required=False, allow_null=True)

    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError("La quantité ne peut pas être nulle.")
        return value

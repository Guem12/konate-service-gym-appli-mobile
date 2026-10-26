from django.db.models import F, Sum
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from catalog.models import ProductVariant
from core.permissions import IsOwner, IsStockManagerOrOwner
from inventory.models import StockMovement, Supplier
from inventory.serializers import (
    StockAdjustmentSerializer,
    StockMovementSerializer,
    SupplierSerializer,
)
from inventory.services import record_movement


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [IsStockManagerOrOwner]
    queryset = Supplier.objects.all()
    search_fields = ["name", "contact_name", "phone"]
    pagination_class = None


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsStockManagerOrOwner]
    filterset_fields = ["movement_type", "variant"]
    search_fields = ["variant__product__name", "variant__sku", "reason"]
    ordering_fields = ["created_at", "quantity"]

    def get_queryset(self):
        return StockMovement.objects.select_related(
            "variant__product", "user", "supplier", "order"
        ).all()

    @action(detail=False, methods=["post"], permission_classes=[IsStockManagerOrOwner])
    def adjust(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        quantity = data["quantity"]
        if data["movement_type"] in {
            StockMovement.Type.BREAKAGE, StockMovement.Type.SALE
        }:
            quantity = -abs(quantity)
        elif data["movement_type"] in {
            StockMovement.Type.IN, StockMovement.Type.RETURN, StockMovement.Type.RESTOCK
        }:
            quantity = abs(quantity)
        supplier = None
        if data.get("supplier"):
            supplier = Supplier.objects.filter(pk=data["supplier"]).first()
        movement = record_movement(
            variant_id=data["variant"],
            quantity=quantity,
            movement_type=data["movement_type"],
            user=request.user,
            reason=data.get("reason", ""),
            supplier=supplier,
        )
        return Response(StockMovementSerializer(movement).data, status=201)

    @action(detail=False, methods=["get"], permission_classes=[IsStockManagerOrOwner])
    def low_stock(self, request):
        variants = (
            ProductVariant.objects.filter(is_active=True, stock_qty__lte=F("low_stock_threshold"))
            .select_related("product")
            .order_by("stock_qty")[:100]
        )
        data = [
            {
                "id": v.id,
                "product_id": v.product_id,
                "product_name": v.product.name,
                "variant_label": v.label,
                "sku": v.sku,
                "stock_qty": v.stock_qty,
                "low_stock_threshold": v.low_stock_threshold,
                "price_purchase": v.price_purchase,
                "price_sale": v.price_sale,
            }
            for v in variants
        ]
        return Response({"count": len(data), "results": data})

    @action(detail=False, methods=["get"], permission_classes=[IsOwner])
    def value(self, request):
        variants = ProductVariant.objects.filter(is_active=True)
        total_purchase = sum(v.stock_qty * v.price_purchase for v in variants)
        total_sale = sum(v.stock_qty * v.price_sale for v in variants)
        return Response(
            {
                "stock_value_purchase": total_purchase,
                "stock_value_sale": total_sale,
                "variants_count": variants.count(),
                "units_count": variants.aggregate(total=Sum("stock_qty"))["total"] or 0,
            }
        )

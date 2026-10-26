from rest_framework import serializers

from catalog.serializers import ProductVariantSerializer
from orders.models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


def _image_url(image, request):
    if not image:
        return None
    return request.build_absolute_uri(image.url) if request else image.url


def _product_image(product, request):
    images = list(product.images.all())
    image = next((img for img in images if img.is_primary), images[0] if images else None)
    return _image_url(image.image, request) if image else None


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="variant.product_id", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    variant_label = serializers.CharField(source="variant.label", read_only=True)
    unit_price = serializers.IntegerField(source="variant.price_sale", read_only=True)
    stock_qty = serializers.IntegerField(source="variant.stock_qty", read_only=True)
    image = serializers.SerializerMethodField()
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = [
            "id", "variant", "product_id", "product_name", "product_slug",
            "variant_label", "unit_price", "quantity", "line_total", "stock_qty", "image",
        ]

    def get_image(self, obj):
        return _product_image(obj.variant.product, self.context.get("request"))


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.ReadOnlyField()
    discount = serializers.ReadOnlyField()
    total = serializers.ReadOnlyField()
    item_count = serializers.ReadOnlyField()
    coupon_code = serializers.CharField(source="coupon.code", read_only=True, default="")

    class Meta:
        model = Cart
        fields = ["id", "items", "subtotal", "discount", "total", "item_count", "coupon_code", "updated_at"]


class CartItemWriteSerializer(serializers.Serializer):
    variant = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class CouponApplySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=30)


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="variant.product_id", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id", "variant", "product_id", "product_slug", "product_name", "variant_label",
            "sku", "quantity", "unit_price_sale", "line_total_sale", "serial_number", "image",
        ]

    def get_image(self, obj):
        return _product_image(obj.variant.product, self.context.get("request"))


class StatusHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True, default="")

    class Meta:
        model = OrderStatusHistory
        fields = ["id", "status", "status_display", "note", "user_name", "created_at"]


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_display = serializers.ReadOnlyField()
    item_count = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    item_names = serializers.SerializerMethodField()
    can_cancel = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id", "number", "status", "status_display", "payment_status",
            "payment_status_display", "total", "amount_paid", "balance_due",
            "item_count", "image", "item_names", "channel", "fulfillment",
            "can_cancel", "created_at", "delivered_at",
        ]

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_image(self, obj):
        item = next(iter(obj.items.all()), None)
        return _product_image(item.variant.product, self.context.get("request")) if item else None

    def get_item_names(self, obj):
        return [item.product_name for item in obj.items.all()[:3]]


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payments = serializers.SerializerMethodField()
    delivery = serializers.SerializerMethodField()
    timeline = StatusHistorySerializer(source="status_history", many=True, read_only=True)
    delivery_address = serializers.ReadOnlyField(source="delivery_address_text")
    customer_phone_display = serializers.CharField(source="customer_phone", read_only=True)
    margin = serializers.SerializerMethodField()
    internal_note = serializers.CharField(read_only=True)
    note = serializers.CharField(read_only=True)
    whatsapp_url = serializers.SerializerMethodField()

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "items", "payments", "delivery", "timeline", "delivery_address",
            "delivery_district", "delivery_street", "delivery_landmark", "delivery_phone",
            "delivery_slot", "desired_date", "customer_name", "customer_phone",
            "customer_phone_display", "subtotal", "discount", "delivery_fee", "coupon_code",
            "note", "internal_note", "margin", "whatsapp_url", "address", "created_at",
        ]

    def get_payments(self, obj):
        from payments.serializers import PaymentSerializer

        return PaymentSerializer(
            obj.payments.all(), many=True, context=self.context
        ).data

    def get_delivery(self, obj):
        from deliveries.serializers import DeliverySerializer

        delivery = getattr(obj, "delivery", None)
        if not delivery:
            return None
        return DeliverySerializer(delivery, context=self.context).data

    def get_margin(self, obj):
        if not self.context.get("include_margin"):
            return None
        return obj.margin

    def get_whatsapp_url(self, obj):
        from core.models import ShopSetting
        from core.whatsapp import order_whatsapp_message, whatsapp_link

        return whatsapp_link(ShopSetting.load().whatsapp_phone, order_whatsapp_message(obj))


class CheckoutSerializer(serializers.Serializer):
    items = CartItemWriteSerializer(many=True, required=False)
    address = serializers.IntegerField(required=False, allow_null=True)
    address_data = serializers.DictField(required=False)
    fulfillment = serializers.ChoiceField(
        choices=Order.Fulfillment.choices, default=Order.Fulfillment.DELIVERY
    )
    payment_method = serializers.ChoiceField(
        choices=[("cash", "Espèces"), ("orange_money", "Orange Money")], default="cash"
    )
    payment_reference = serializers.CharField(required=False, allow_blank=True, max_length=60)
    payment_amount = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    coupon_code = serializers.CharField(required=False, allow_blank=True, max_length=30)
    client_reference = serializers.UUIDField(required=False, allow_null=True)
    delivery_slot = serializers.CharField(required=False, allow_blank=True, max_length=80)
    desired_date = serializers.DateField(required=False, allow_null=True)

    def validate_items(self, value):
        if value is not None and len(value) == 0:
            raise serializers.ValidationError("Ajoutez au moins un article.")
        return value


class AdminOrderCreateSerializer(CheckoutSerializer):
    user = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    customer_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    customer = serializers.IntegerField(required=False, allow_null=True)
    channel = serializers.ChoiceField(choices=Order.Channel.choices, default=Order.Channel.COUNTER)
    mark_paid = serializers.BooleanField(default=False)
    internal_note = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Ajoutez au moins un article à la commande.")
        return value

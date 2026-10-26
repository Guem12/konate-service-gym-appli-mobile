from django.contrib import admin

from orders.models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_label", "quantity", "unit_price_sale", "unit_price_purchase")
    can_delete = False


class StatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("status", "note", "user", "created_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "customer_name", "status", "payment_status_display", "total", "amount_paid", "balance_due", "created_at")
    list_filter = ("status", "channel", "fulfillment", "created_at")
    search_fields = ("number", "customer_phone", "customer_name")
    readonly_fields = ("number", "subtotal", "total", "amount_paid", "balance_due", "created_at", "updated_at")
    inlines = [OrderItemInline, StatusHistoryInline]
    date_hierarchy = "created_at"

    @admin.display(description="paiement")
    def payment_status_display(self, obj):
        return obj.payment_status_display


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    inlines = [CartItemInline]

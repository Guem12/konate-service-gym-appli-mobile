from django.contrib import admin
from django.utils.html import format_html

from deliveries.models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "courier_name", "slot", "delivery_cost", "amount_collected", "delivered_at")
    list_filter = ("status", "courier_name")
    search_fields = ("order__number", "order__customer_name", "courier_name")

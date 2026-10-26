from django.contrib import admin

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "amount", "status", "om_reference", "confirmed_at", "created_at")
    list_filter = ("status", "method", "created_at")
    search_fields = ("order__number", "om_reference", "payer_phone")
    readonly_fields = ("confirmed_at",)

from django.contrib import admin

from inventory.models import StockMovement, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "phone", "is_active")
    search_fields = ("name", "contact_name", "phone")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "variant", "movement_type", "quantity", "stock_after", "reason", "user")
    list_filter = ("movement_type", "created_at")
    search_fields = ("variant__product__name", "variant__sku", "reason")
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

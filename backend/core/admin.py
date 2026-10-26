from django.contrib import admin
from django.utils.html import format_html

from core.models import AuditLog, Notification, ShopSetting


@admin.register(ShopSetting)
class ShopSettingAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "whatsapp_phone", "orange_money_phone", "address")

    def has_add_permission(self, request):
        return not ShopSetting.objects.exists()


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "target_type", "target_id", "detail")
    list_filter = ("action",)
    search_fields = ("detail", "target_id", "user__phone")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "is_read", "created_at")
    search_fields = ("title", "user__phone")

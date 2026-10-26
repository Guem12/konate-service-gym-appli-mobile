from django.db import models
from rest_framework import serializers

from .models import Notification, ShopSetting


class ShopSettingSerializer(serializers.ModelSerializer):
    whatsapp_url = serializers.SerializerMethodField()

    class Meta:
        model = ShopSetting
        fields = [
            "shop_name", "logo", "whatsapp_phone", "orange_money_phone", "phone",
            "email", "address", "opening_hours", "delivery_note", "delivery_zones",
            "delivery_slots", "return_delay_days", "low_stock_threshold",
            "whatsapp_product_template", "whatsapp_order_template", "currency",
            "free_delivery", "whatsapp_url",
        ]

    def get_whatsapp_url(self, obj):
        from core.whatsapp import whatsapp_link

        return whatsapp_link(obj.whatsapp_phone, "Bonjour Konaté Service Gym !")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "order", "is_read", "created_at"]

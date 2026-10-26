from django.urls import path

from core.views import (
    AdminShopSettingView,
    HealthView,
    NotificationListView,
    NotificationReadView,
    ShopSettingView,
    WhatsAppLinkView,
)

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("settings", ShopSettingView.as_view(), name="shop-settings"),
    path("admin/settings", AdminShopSettingView.as_view(), name="admin-shop-settings"),
    path("whatsapp/link", WhatsAppLinkView.as_view(), name="whatsapp-link"),
    path("me/notifications", NotificationListView.as_view(), name="my-notifications"),
    path("me/notifications/<int:pk>/read", NotificationReadView.as_view(), name="notification-read"),
]

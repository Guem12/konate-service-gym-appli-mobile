from django.urls import include, path
from rest_framework.routers import DefaultRouter

from orders.views import (
    AdminOrderViewSet,
    CartCouponView,
    CartItemDetailView,
    CartItemsView,
    CartView,
    OrderViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register("orders", OrderViewSet, basename="order")
router.register("admin/orders", AdminOrderViewSet, basename="admin-order")

urlpatterns = [
    path("cart", CartView.as_view(), name="cart"),
    path("cart/items", CartItemsView.as_view(), name="cart-items"),
    path("cart/items/<int:pk>", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("cart/coupon", CartCouponView.as_view(), name="cart-coupon"),
    path("home", OrderViewSet.as_view({"get": "home"}), name="home"),
    path("", include(router.urls)),
]
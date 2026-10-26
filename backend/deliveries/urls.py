from django.urls import include, path
from rest_framework.routers import DefaultRouter

from deliveries.views import AdminDeliveryViewSet

router = DefaultRouter(trailing_slash=False)
router.register("admin/deliveries", AdminDeliveryViewSet, basename="admin-delivery")

urlpatterns = [path("", include(router.urls))]

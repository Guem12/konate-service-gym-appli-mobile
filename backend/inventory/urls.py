from django.urls import include, path
from rest_framework.routers import DefaultRouter

from inventory.views import StockMovementViewSet, SupplierViewSet

router = DefaultRouter(trailing_slash=False)
router.register("admin/stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("admin/suppliers", SupplierViewSet, basename="supplier")

urlpatterns = [path("", include(router.urls))]

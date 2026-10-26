from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payments.views import AdminPaymentViewSet

router = DefaultRouter(trailing_slash=False)
router.register("admin/payments", AdminPaymentViewSet, basename="admin-payment")

urlpatterns = [path("", include(router.urls))]

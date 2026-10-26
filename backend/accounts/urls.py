from django.urls import path

from accounts.views import (
    AddressDetailView,
    AddressListCreateView,
    AdminCustomerBlockView,
    AdminCustomerDetailView,
    AdminCustomerListView,
    AdminCustomerQuickCreateView,
    AdminCustomerResetPasswordView,
    AdminCustomerWhatsAppView,
    AdminStaffDetailView,
    AdminStaffListCreateView,
    ChangePasswordView,
    DeviceTokenView,
)

urlpatterns = [
    path("me/addresses", AddressListCreateView.as_view(), name="address-list"),
    path("me/addresses/<int:pk>", AddressDetailView.as_view(), name="address-detail"),
    path("me/devices", DeviceTokenView.as_view(), name="device-tokens"),
    path("me/change-password", ChangePasswordView.as_view(), name="change-password"),
    path("admin/customers", AdminCustomerListView.as_view(), name="admin-customers"),
    path("admin/customers/quick-create", AdminCustomerQuickCreateView.as_view(), name="admin-customer-quick"),
    path("admin/customers/<int:pk>", AdminCustomerDetailView.as_view(), name="admin-customer-detail"),
    path("admin/customers/<int:pk>/block", AdminCustomerBlockView.as_view(), name="admin-customer-block"),
    path("admin/customers/<int:pk>/reset-password", AdminCustomerResetPasswordView.as_view(), name="admin-customer-reset"),
    path("admin/customers/<int:pk>/whatsapp", AdminCustomerWhatsAppView.as_view(), name="admin-customer-whatsapp"),
    path("admin/users", AdminStaffListCreateView.as_view(), name="admin-users"),
    path("admin/users/<int:pk>", AdminStaffDetailView.as_view(), name="admin-user-detail"),
]

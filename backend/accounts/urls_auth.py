from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.auth_views import (
    DeleteAccountView,
    LoginView,
    MeView,
    PasswordResetRequestView,
    RegisterView,
    TwoFactorConfirmView,
    TwoFactorSetupView,
    TwoFactorStatusView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("password-reset", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("me", MeView.as_view(), name="auth-me"),
    path("me/delete", DeleteAccountView.as_view(), name="auth-delete-account"),
    path("2fa/setup", TwoFactorSetupView.as_view(), name="auth-2fa-setup"),
    path("2fa/confirm", TwoFactorConfirmView.as_view(), name="auth-2fa-confirm"),
    path("2fa/status", TwoFactorStatusView.as_view(), name="auth-2fa-status"),
]

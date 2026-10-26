from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import parsers, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView  # noqa: F401

from accounts.models import User
from accounts.serializers import (
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    TwoFactorSetupSerializer,
    UserSerializer,
)
from accounts.services import (
    generate_temp_password,
    generate_totp_secret,
    log_action,
    send_password_reset_code,
    tokens_for_user,
    totp_uri,
    verify_totp,
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens_for_user(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: dict})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        password = serializer.validated_data["password"]
        otp_code = serializer.validated_data.get("otp_code", "")

        user = User.objects.filter(phone=phone).first()
        generic_error = Response(
            {"detail": "Numéro ou mot de passe incorrect."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
        if user is None:
            return generic_error
        if user.is_locked:
            minutes = max(1, int((user.locked_until - timezone.now()).total_seconds() // 60) + 1)
            return Response(
                {
                    "detail": (
                        f"Compte temporairement verrouillé après plusieurs échecs. "
                        f"Réessayez dans {minutes} minute(s)."
                    ),
                    "code": "locked",
                },
                status=status.HTTP_423_LOCKED,
            )
        if user.is_blocked:
            return Response(
                {"detail": "Votre compte a été bloqué. Contactez la boutique sur WhatsApp.",
                 "code": "blocked"},
                status=status.HTTP_403_FORBIDDEN,
            )

        authenticated = authenticate(request, username=phone, password=password)
        if authenticated is None:
            user.register_failed_login(
                settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCKOUT_MINUTES
            )
            return generic_error

        if (
            settings.ADMIN_2FA_REQUIRED
            and authenticated.is_staff_role
            and authenticated.two_factor_enabled
        ):
            if not otp_code:
                return Response(
                    {
                        "detail": "Saisissez le code de votre application d'authentification.",
                        "code": "otp_required",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not verify_totp(authenticated, otp_code):
                authenticated.register_failed_login(
                    settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCKOUT_MINUTES
                )
                return Response(
                    {"detail": "Code de double authentification invalide.", "code": "otp_invalid"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        authenticated.reset_failed_logins()
        authenticated.last_login_ip = request.META.get("REMOTE_ADDR")
        authenticated.save(update_fields=["last_login_ip"])

        return Response(
            {
                "user": UserSerializer(authenticated, context={"request": request}).data,
                "tokens": tokens_for_user(authenticated),
                "two_factor_setup_required": bool(
                    authenticated.is_staff_role
                    and settings.ADMIN_2FA_REQUIRED
                    and not authenticated.two_factor_enabled
                ),
            }
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    @extend_schema(request=ProfileUpdateSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        from orders.models import Order

        Order.objects.filter(user=user).update(
            user=None,
            customer_name=f"{user.full_name} (compte supprimé)",
            customer_phone=user.phone,
        )
        user.addresses.all().delete()
        user.device_tokens.all().delete()
        user.favorites.all().delete() if hasattr(user, "favorites") else None
        user.anonymize()
        log_action(user, "role_change", "user", user.pk, "Suppression du compte client")
        return Response({"detail": "Votre compte et vos données ont été supprimés."})


class PasswordResetRequestView(APIView):
    """Demande de réinitialisation : contact WhatsApp avec message prérempli."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        from core.whatsapp import normalize_phone

        normalized = normalize_phone(request.data.get("phone", ""))
        user = User.objects.filter(phone=normalized).first()
        link = send_password_reset_code(user) if user else None
        return Response(
            {
                "detail": (
                    "Si un compte existe avec ce numéro, contactez la boutique sur WhatsApp "
                    "pour réinitialiser votre mot de passe."
                ),
                "whatsapp_url": link,
            }
        )


class TwoFactorSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_staff_role:
            return Response(
                {"detail": "La double authentification est réservée aux comptes d'administration."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.two_factor_enabled:
            return Response({"detail": "La double authentification est déjà active."}, status=400)
        user.totp_secret = generate_totp_secret()
        user.save(update_fields=["totp_secret"])
        return Response({"secret": user.totp_secret, "otpauth_url": totp_uri(user)})


class TwoFactorConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TwoFactorSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not verify_totp(user, serializer.validated_data["code"]):
            return Response({"detail": "Code invalide. Réessayez."}, status=400)
        user.two_factor_enabled = True
        user.save(update_fields=["two_factor_enabled"])
        log_action(user, "role_change", "user", user.pk, "Activation de la double authentification")
        return Response({"detail": "Double authentification activée."})


class TwoFactorStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"enabled": request.user.two_factor_enabled})

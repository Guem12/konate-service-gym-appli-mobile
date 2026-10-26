from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Address, DeviceToken, User
from accounts.serializers import (
    AddressSerializer,
    AdminCustomerSerializer,
    BlockCustomerSerializer,
    ChangePasswordSerializer,
    DeviceTokenSerializer,
    ResetPasswordSerializer,
    StaffSerializer,
)
from accounts.services import generate_temp_password, log_action
from core.permissions import IsAdminRole, IsOwner
from core.whatsapp import whatsapp_link


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class DeviceTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Appareil enregistré pour les notifications."}, status=201)

    def delete(self, request):
        token = request.data.get("token", "")
        DeviceToken.objects.filter(user=request.user, token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Mot de passe modifié."})


class AdminCustomerListView(generics.ListAPIView):
    serializer_class = AdminCustomerSerializer
    permission_classes = [IsAdminRole]
    search_fields = ["full_name", "phone"]
    ordering_fields = ["created_at", "full_name"]
    filterset_fields = ["is_blocked"]

    def get_queryset(self):
        return User.objects.filter(role=User.Role.CLIENT).annotate(
            orders_count=Count("orders", distinct=True)
        )


class AdminCustomerDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminCustomerSerializer
    permission_classes = [IsAdminRole]
    queryset = User.objects.filter(role=User.Role.CLIENT)


class AdminCustomerBlockView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        customer = User.objects.filter(pk=pk, role=User.Role.CLIENT).first()
        if not customer:
            return Response({"detail": "Client introuvable."}, status=404)
        serializer = BlockCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer.is_blocked = serializer.validated_data["is_blocked"]
        customer.block_reason = serializer.validated_data.get("reason", "")
        customer.save(update_fields=["is_blocked", "block_reason"])
        log_action(
            request.user, "customer_block", "user", customer.pk,
            f"{'Blocage' if customer.is_blocked else 'Déblocage'} : {customer.block_reason}",
        )
        return Response(AdminCustomerSerializer(customer).data)


class AdminCustomerResetPasswordView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        customer = User.objects.filter(pk=pk).first()
        if not customer:
            return Response({"detail": "Utilisateur introuvable."}, status=404)
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get("new_password") or generate_temp_password()
        customer.set_password(password)
        customer.failed_login_count = 0
        customer.locked_until = None
        customer.save()
        log_action(request.user, "role_change", "user", customer.pk, "Réinitialisation du mot de passe")
        return Response(
            {
                "detail": "Mot de passe réinitialisé. Communiquez-le au client par WhatsApp.",
                "temporary_password": password,
            }
        )


class AdminCustomerWhatsAppView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        customer = User.objects.filter(pk=pk).first()
        if not customer:
            return Response({"detail": "Client introuvable."}, status=404)
        message = request.query_params.get(
            "message", f"Bonjour {customer.full_name}, c'est Konaté Service Gym."
        )
        return Response(
            {"url": whatsapp_link(customer.phone, message), "phone": customer.phone_display}
        )


class AdminStaffListCreateView(generics.ListCreateAPIView):
    serializer_class = StaffSerializer
    permission_classes = [IsOwner]
    queryset = User.objects.exclude(role=User.Role.CLIENT).order_by("full_name")
    pagination_class = None

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(self.request.user, "role_change", "user", user.pk, f"Création du compte {user.role}")


class AdminStaffDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StaffSerializer
    permission_classes = [IsOwner]
    queryset = User.objects.exclude(role=User.Role.CLIENT)

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(self.request.user, "role_change", "user", user.pk, f"Rôle : {user.role}")

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({"detail": "Vous ne pouvez pas supprimer votre propre compte."}, status=400)
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCustomerQuickCreateView(APIView):
    """Création rapide d'un client depuis l'administration (vente comptoir)."""

    permission_classes = [IsOwner]

    def post(self, request):
        from accounts.serializers import RegisterSerializer

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminCustomerSerializer(user).data, status=201)

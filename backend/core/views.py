from django.http import FileResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Notification, ShopSetting
from core.permissions import IsAdminRole, IsStaffRole
from core.pdf import invoice_pdf
from core.serializers import NotificationSerializer, ShopSettingSerializer
from core.whatsapp import whatsapp_link


class ShopSettingView(APIView):
    """Paramètres publics de la boutique (numéros WhatsApp / Orange Money)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=ShopSettingSerializer)
    def get(self, request):
        return Response(ShopSettingSerializer(ShopSetting.load()).data)


class AdminShopSettingView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(request=ShopSettingSerializer, responses=ShopSettingSerializer)
    def patch(self, request):
        serializer = ShopSettingSerializer(ShopSetting.load(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WhatsAppLinkView(APIView):
    """Renvoie un lien wa.me prérempli (produit, commande ou contact direct)."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = "anon"

    @extend_schema(
        parameters=[
            OpenApiParameter("message", str, description="Message prérempli"),
            OpenApiParameter("order", str, description="Numéro de commande"),
            OpenApiParameter("product", int, description="Identifiant de produit"),
        ],
        responses={200: dict},
    )
    def get(self, request):
        from catalog.models import Product
        from core.whatsapp import order_whatsapp_message, product_whatsapp_message
        from orders.models import Order

        setting = ShopSetting.load()
        message = request.query_params.get("message", "")
        order_param = request.query_params.get("order")
        product_param = request.query_params.get("product")

        if product_param:
            try:
                product = Product.objects.get(pk=product_param)
                message = product_whatsapp_message(product)
            except (Product.DoesNotExist, ValueError):
                return Response({"detail": "Produit introuvable."}, status=404)
        elif order_param:
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Authentification requise pour partager une commande."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            order = Order.objects.filter(
                number=order_param, user=request.user
            ).first()
            if not order and request.user.is_authenticated and request.user.is_staff_role:
                # Les admins peuvent accéder à toutes les commandes
                order = Order.objects.filter(number=order_param).first()
            if not order:
                return Response({"detail": "Commande introuvable."}, status=404)
            message = order_whatsapp_message(order)

        return Response({"url": whatsapp_link(setting.whatsapp_phone, message), "message": message})


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
        return Response({"detail": "Notification marquée comme lue."})


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "API Konaté-Service-Gym",
                "version": "1.0.0",
                "time": timezone.now().isoformat(),
            }
        )

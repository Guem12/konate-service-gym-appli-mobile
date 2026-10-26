import base64
import uuid

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Address, DeviceToken, User
from core.whatsapp import normalize_phone


class AddressSerializer(serializers.ModelSerializer):
    full_text = serializers.ReadOnlyField()

    class Meta:
        model = Address
        fields = [
            "id", "label", "district", "street", "landmark", "phone",
            "latitude", "longitude", "is_default", "full_text",
        ]

    def validate_phone(self, value):
        return normalize_phone(value) if value else value

    def create(self, validated_data):
        if validated_data.get("is_default"):
            Address.objects.filter(user=validated_data["user"]).update(is_default=False)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default"):
            Address.objects.filter(user=instance.user).update(is_default=False)
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    phone_display = serializers.ReadOnlyField()
    is_staff_role = serializers.ReadOnlyField()
    photo_url = serializers.SerializerMethodField()
    addresses = AddressSerializer(many=True, read_only=True)
    orders_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "phone", "phone_display", "full_name", "email", "photo", "photo_url", "role",
            "is_staff_role", "is_blocked", "two_factor_enabled", "addresses",
            "orders_count", "total_spent", "balance_due", "created_at",
        ]
        read_only_fields = ["phone", "role", "is_blocked", "two_factor_enabled", "created_at"]

    def get_photo_url(self, obj):
        if not obj.photo:
            return None
        request = self.context.get("request")
        url = obj.photo.url
        return request.build_absolute_uri(url) if request else url

    def get_orders_count(self, obj):
        return obj.orders.count()

    def get_total_spent(self, obj):
        from django.db.models import Sum

        return obj.orders.filter(status__in=["delivered", "shipping", "preparing", "confirmed"]).aggregate(
            total=Sum("amount_paid")
        )["total"] or 0

    def get_balance_due(self, obj):
        from django.db.models import Sum

        return obj.orders.exclude(status__in=["cancelled", "returned"]).aggregate(
            total=Sum("balance_due")
        )["total"] or 0


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        if len(normalized) != 11 or not normalized.startswith("223"):
            raise serializers.ValidationError(
                "Numéro malien invalide. Exemple : 70 00 00 00 ou +223 70 00 00 00."
            )
        if User.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError(
                "Un compte existe déjà avec ce numéro. Connectez-vous."
            )
        return normalized

    def validate_full_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Indiquez votre nom complet.")
        return value.strip()

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(required=False, allow_blank=True, max_length=10)

    def validate_phone(self, value):
        return normalize_phone(value)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(max_length=120, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    photo = serializers.ImageField(required=False, allow_null=True)
    photo_base64 = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ["full_name", "email", "photo", "photo_base64"]

    def update(self, instance, validated_data):
        photo_b64 = validated_data.pop("photo_base64", None)
        if photo_b64:
            if photo_b64.upper() == "DELETE":
                if instance.photo:
                    instance.photo.delete(save=False)
                instance.photo = None
            else:
                if "," in photo_b64:
                    _, photo_b64 = photo_b64.split(",", 1)
                try:
                    decoded = base64.b64decode(photo_b64)
                    filename = f"avatar_{instance.id}_{uuid.uuid4().hex[:6]}.jpg"
                    instance.photo.save(filename, ContentFile(decoded), save=False)
                except Exception:
                    raise serializers.ValidationError({"photo_base64": "Image base64 invalide."})
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Ancien mot de passe incorrect.")
        return value


class AdminCustomerSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["block_reason", "last_login"]


class BlockCustomerSerializer(serializers.Serializer):
    is_blocked = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=False, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    phone_display = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id", "phone", "phone_display", "full_name", "role", "is_active",
            "two_factor_enabled", "password", "last_login", "created_at",
        ]
        read_only_fields = ["two_factor_enabled", "last_login", "created_at"]

    def validate_role(self, value):
        if value == User.Role.CLIENT:
            raise serializers.ValidationError(
                "Un compte d'administration doit avoir le rôle vendeur, "
                "gestionnaire de stock ou propriétaire."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Le mot de passe est obligatoire."})
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["token", "platform"]

    def create(self, validated_data):
        token, _ = DeviceToken.objects.update_or_create(
            token=validated_data["token"],
            defaults={"user": self.context["request"].user, "platform": validated_data.get("platform", "android")},
        )
        return token


class TwoFactorSetupSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)

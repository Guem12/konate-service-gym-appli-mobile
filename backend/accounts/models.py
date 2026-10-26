from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from core.whatsapp import normalize_phone

PHONE_VALIDATOR = RegexValidator(
    regex=r"^223\d{8}$",
    message="Numéro invalide. Utilisez un numéro malien à 8 chiffres (ex. 70 00 00 00).",
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, full_name, password=None, **extra_fields):
        if not phone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        normalized = normalize_phone(phone)
        if not normalized:
            raise ValueError("Numéro de téléphone invalide.")
        user = self.model(phone=normalized, full_name=full_name.strip(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.OWNER)
        extra_fields.setdefault("two_factor_enabled", False)
        return self.create_user(phone, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Compte client ou membre de l'administration (téléphone = identifiant)."""

    class Role(models.TextChoices):
        CLIENT = "client", "Client"
        OWNER = "owner", "Propriétaire"
        VENDOR = "vendor", "Vendeur"
        STOCK_MANAGER = "stock_manager", "Gestionnaire de stock"

    STAFF_ROLES = (Role.OWNER, Role.VENDOR, Role.STOCK_MANAGER)

    phone = models.CharField(
        "téléphone", max_length=20, unique=True, validators=[PHONE_VALIDATOR],
        help_text="Format international sans + : 223XXXXXXXX",
    )
    full_name = models.CharField("nom complet", max_length=120)
    email = models.EmailField("e-mail", blank=True)
    photo = models.ImageField("photo de profil", upload_to="profiles/", blank=True, null=True)
    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.CLIENT)
    is_active = models.BooleanField("actif", default=True)
    is_staff = models.BooleanField("accès admin Django", default=False)
    is_blocked = models.BooleanField("bloqué", default=False)
    block_reason = models.CharField("motif du blocage", max_length=200, blank=True)
    is_staff_account = models.BooleanField("compte d'administration", default=False)

    # Sécurité
    failed_login_count = models.PositiveIntegerField("échecs de connexion", default=0)
    locked_until = models.DateTimeField("verrouillé jusqu'à", null=True, blank=True)
    last_login_ip = models.GenericIPAddressField("dernière IP", null=True, blank=True)
    two_factor_enabled = models.BooleanField("double authentification", default=False)
    totp_secret = models.CharField("secret TOTP", max_length=64, blank=True)

    created_at = models.DateTimeField("inscrit le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.phone_display})"

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        self.is_staff_account = self.role in self.STAFF_ROLES
        if self.role in self.STAFF_ROLES:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def phone_display(self):
        digits = self.phone
        if len(digits) == 11:
            return f"+{digits[:3]} {digits[3:5]} {digits[5:7]} {digits[7:9]} {digits[9:]}"
        return f"+{digits}"

    @property
    def is_staff_role(self):
        return self.role in self.STAFF_ROLES

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def whatsapp_phone(self):
        return self.phone

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_login(self, max_attempts=5, lockout_minutes=15):
        self.failed_login_count += 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
            self.failed_login_count = 0
        self.save(update_fields=["failed_login_count", "locked_until", "updated_at"])

    def reset_failed_logins(self):
        if self.failed_login_count or self.locked_until:
            self.failed_login_count = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_count", "locked_until", "updated_at"])

    def anonymize(self):
        """Suppression du compte à la demande du client (données personnelles)."""
        self.phone = f"22300000000{self.pk}"[-11:]
        self.full_name = "Compte supprimé"
        self.email = ""
        self.is_active = False
        self.is_blocked = True
        self.two_factor_enabled = False
        self.totp_secret = ""
        self.set_unusable_password()
        self.save()


class Address(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses", verbose_name="client"
    )
    label = models.CharField("libellé", max_length=60, default="Domicile")
    district = models.CharField("quartier", max_length=80)
    street = models.CharField("rue", max_length=160, blank=True)
    landmark = models.CharField("point de repère", max_length=160, blank=True)
    phone = models.CharField("téléphone", max_length=20, blank=True)
    latitude = models.DecimalField(
        "latitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        "longitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    is_default = models.BooleanField("adresse par défaut", default=False)
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        verbose_name = "adresse"
        verbose_name_plural = "adresses"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.label} — {self.district}"

    @property
    def full_text(self):
        parts = [self.district, self.street, self.landmark]
        return ", ".join(part for part in parts if part)


class DeviceToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="device_tokens", verbose_name="utilisateur"
    )
    token = models.CharField("jeton FCM", max_length=255, unique=True)
    platform = models.CharField(
        "plateforme", max_length=10, choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")],
        default="android",
    )
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "jeton d'appareil"
        verbose_name_plural = "jetons d'appareil"

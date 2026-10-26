from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Ajoute created_at / updated_at à tous les modèles métier."""

    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


class ShopSetting(TimeStampedModel):
    """Paramètres uniques de la boutique (singleton)."""

    shop_name = models.CharField("nom de la boutique", max_length=120, default="Konaté Service Gym")
    logo = models.ImageField("logo", upload_to="shop/", blank=True, null=True)
    whatsapp_phone = models.CharField("numéro WhatsApp", max_length=20, default="22370000000")
    orange_money_phone = models.CharField("numéro Orange Money", max_length=20, default="22370000000")
    phone = models.CharField("téléphone", max_length=20, blank=True)
    email = models.EmailField("e-mail", blank=True)
    address = models.CharField("adresse", max_length=255, default="Bamako, Mali")
    opening_hours = models.CharField("horaires", max_length=160, default="Lun-Sam : 08h-20h")
    delivery_note = models.CharField(
        "note livraison", max_length=200, default="Livraison gratuite à Bamako"
    )
    delivery_zones = models.JSONField("zones de livraison", default=list, blank=True)
    delivery_slots = models.JSONField("créneaux de livraison", default=list, blank=True)
    return_delay_days = models.PositiveIntegerField("délai de retour (jours)", default=7)
    low_stock_threshold = models.PositiveIntegerField("seuil de stock par défaut", default=3)
    whatsapp_product_template = models.TextField(
        "modèle WhatsApp produit",
        default=(
            "Bonjour Konaté Service Gym, je suis intéressé(e) par : {product} "
            "({price}). Est-il disponible ?"
        ),
    )
    whatsapp_order_template = models.TextField(
        "modèle WhatsApp commande",
        default=(
            "Bonjour Konaté Service Gym, je souhaite discuter de ma commande "
            "{order_number} d'un montant de {total}."
        ),
    )
    currency = models.CharField("devise", max_length=8, default="FCFA")
    free_delivery = models.BooleanField("livraison gratuite", default=True)

    class Meta:
        verbose_name = "paramètres de la boutique"
        verbose_name_plural = "paramètres de la boutique"

    def __str__(self):
        return self.shop_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AuditLog(models.Model):
    """Journal des actions sensibles (prix, annulation, rôles...)."""

    ACTIONS = [
        ("product_price_change", "Modification de prix"),
        ("product_delete", "Suppression de produit"),
        ("order_cancel", "Annulation de commande"),
        ("order_return", "Retour de commande"),
        ("payment_confirm", "Confirmation de paiement"),
        ("payment_reject", "Rejet de paiement"),
        ("stock_adjust", "Correction de stock"),
        ("role_change", "Changement de rôle"),
        ("customer_block", "Blocage de client"),
        ("settings_update", "Modification des paramètres"),
    ]

    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="audit_logs",
        verbose_name="utilisateur",
    )
    action = models.CharField("action", max_length=40, choices=ACTIONS)
    target_type = models.CharField("type de cible", max_length=60, blank=True)
    target_id = models.CharField("identifiant de cible", max_length=60, blank=True)
    detail = models.CharField("détail", max_length=400, blank=True)
    created_at = models.DateTimeField("date", default=timezone.now)

    class Meta:
        verbose_name = "journal d'audit"
        verbose_name_plural = "journal d'audit"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_display()} — {self.user}"


class Notification(models.Model):
    """Notification in-app (miroir des push FCM, consultable sans réseau)."""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications",
        verbose_name="destinataire",
    )
    title = models.CharField("titre", max_length=120)
    body = models.CharField("message", max_length=400)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notifications", verbose_name="commande",
    )
    is_read = models.BooleanField("lue", default=False)
    created_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

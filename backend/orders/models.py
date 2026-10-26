import uuid

from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="cart", verbose_name="client"
    )
    coupon = models.ForeignKey(
        "catalog.Coupon", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="code promo"
    )

    class Meta:
        verbose_name = "panier"
        verbose_name_plural = "paniers"

    def __str__(self):
        return f"Panier de {self.user}"

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def discount(self):
        if not self.coupon:
            return 0
        try:
            return self.coupon.discount_for(self.subtotal)
        except Exception:
            return 0

    @property
    def total(self):
        return max(0, self.subtotal - self.discount)

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name="panier")
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.CASCADE, related_name="cart_items",
        verbose_name="variante",
    )
    quantity = models.PositiveIntegerField("quantité", default=1)
    added_at = models.DateTimeField("ajouté le", auto_now_add=True)

    class Meta:
        verbose_name = "ligne de panier"
        verbose_name_plural = "lignes de panier"
        unique_together = ("cart", "variant")

    def __str__(self):
        return f"{self.variant} × {self.quantity}"

    @property
    def line_total(self):
        return self.variant.price_sale * self.quantity


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "En attente de paiement"
        CONFIRMED = "confirmed", "Confirmée"
        PREPARING = "preparing", "En préparation"
        SHIPPING = "shipping", "En cours de livraison"
        DELIVERED = "delivered", "Livrée"
        CANCELLED = "cancelled", "Annulée"
        RETURNED = "returned", "Retournée"

    class Channel(models.TextChoices):
        APP = "app", "Application"
        WHATSAPP = "whatsapp", "WhatsApp"
        COUNTER = "counter", "Comptoir"

    class Fulfillment(models.TextChoices):
        DELIVERY = "delivery", "Livraison"
        PICKUP = "pickup", "Retrait en boutique"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Non payée"
        PARTIAL = "partial", "Partiellement payée"
        PAID = "paid", "Payée"

    number = models.CharField("numéro", max_length=24, unique=True, blank=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="orders", verbose_name="client",
    )
    customer_name = models.CharField("nom du client", max_length=120, blank=True)
    customer_phone = models.CharField("téléphone du client", max_length=20, blank=True)

    channel = models.CharField("canal", max_length=12, choices=Channel.choices, default=Channel.APP)
    fulfillment = models.CharField(
        "mode de réception", max_length=10, choices=Fulfillment.choices, default=Fulfillment.DELIVERY
    )
    status = models.CharField(
        "statut", max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT
    )

    subtotal = models.PositiveIntegerField("sous-total", default=0)
    discount = models.PositiveIntegerField("remise", default=0)
    total = models.PositiveIntegerField("total", default=0)
    delivery_fee = models.PositiveIntegerField("frais de livraison", default=0)
    amount_paid = models.PositiveIntegerField("montant payé", default=0)
    balance_due = models.PositiveIntegerField("solde dû", default=0)

    coupon = models.ForeignKey(
        "catalog.Coupon", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="code promo"
    )
    coupon_code = models.CharField("code promo utilisé", max_length=30, blank=True)

    address = models.ForeignKey(
        "accounts.Address", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="adresse"
    )
    delivery_district = models.CharField("quartier", max_length=80, blank=True)
    delivery_street = models.CharField("rue", max_length=160, blank=True)
    delivery_landmark = models.CharField("point de repère", max_length=160, blank=True)
    delivery_phone = models.CharField("téléphone livraison", max_length=20, blank=True)
    delivery_slot = models.CharField("créneau souhaité", max_length=80, blank=True)
    desired_date = models.DateField("date souhaitée", null=True, blank=True)

    note = models.TextField("note du client", blank=True)
    internal_note = models.TextField("note interne", blank=True)
    client_reference = models.UUIDField(
        "référence client", null=True, blank=True, unique=True,
        help_text="Identifiant d'idempotence généré par l'application.",
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_orders", verbose_name="créée par",
    )
    stock_restocked = models.BooleanField("stock restitué", default=False)
    cancel_reason = models.CharField("motif d'annulation", max_length=200, blank=True)

    confirmed_at = models.DateTimeField("confirmée le", null=True, blank=True)
    preparing_at = models.DateTimeField("préparée le", null=True, blank=True)
    shipped_at = models.DateTimeField("expédiée le", null=True, blank=True)
    delivered_at = models.DateTimeField("livrée le", null=True, blank=True)
    cancelled_at = models.DateTimeField("annulée le", null=True, blank=True)
    returned_at = models.DateTimeField("retournée le", null=True, blank=True)

    class Meta:
        verbose_name = "commande"
        verbose_name_plural = "commandes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["number"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.number or f"Commande #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.client_reference:
            self.client_reference = None
        self.balance_due = max(0, self.total - self.amount_paid)
        if not self.number:
            super().save(*args, **kwargs)
            self.number = f"KSG-{timezone.localtime(self.created_at):%y%m}-{self.pk:05d}"
            super().save(update_fields=["number"])
            return
        super().save(*args, **kwargs)

    @property
    def payment_status(self):
        if self.amount_paid <= 0:
            return self.PaymentStatus.UNPAID
        if self.amount_paid < self.total:
            return self.PaymentStatus.PARTIAL
        return self.PaymentStatus.PAID

    @property
    def payment_status_display(self):
        return dict(self.PaymentStatus.choices)[self.payment_status]

    @property
    def delivery_address_text(self):
        parts = [self.delivery_district, self.delivery_street, self.delivery_landmark]
        return ", ".join(part for part in parts if part)

    @property
    def can_cancel(self):
        return self.status in {self.Status.PENDING_PAYMENT, self.Status.CONFIRMED} and not self.stock_restocked

    @property
    def is_open(self):
        return self.status not in {
            self.Status.DELIVERED, self.Status.CANCELLED, self.Status.RETURNED
        }

    @property
    def margin(self):
        return sum(item.margin for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="commande")
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.PROTECT, related_name="order_items",
        verbose_name="variante",
    )
    product_name = models.CharField("produit", max_length=160)
    variant_label = models.CharField("variante", max_length=80, blank=True)
    sku = models.CharField("SKU", max_length=60, blank=True)
    quantity = models.PositiveIntegerField("quantité", default=1)
    unit_price_sale = models.PositiveIntegerField("prix de vente unitaire", default=0)
    unit_price_purchase = models.PositiveIntegerField("prix d'achat unitaire", default=0)
    line_total_sale = models.PositiveIntegerField("total vente", default=0)
    line_total_purchase = models.PositiveIntegerField("total achat", default=0)
    serial_number = models.CharField("numéro de série", max_length=80, blank=True)

    class Meta:
        verbose_name = "ligne de commande"
        verbose_name_plural = "lignes de commande"
        ordering = ["id"]

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    def save(self, *args, **kwargs):
        self.line_total_sale = self.unit_price_sale * self.quantity
        self.line_total_purchase = self.unit_price_purchase * self.quantity
        super().save(*args, **kwargs)

    @property
    def margin(self):
        return self.line_total_sale - self.line_total_purchase


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_history", verbose_name="commande"
    )
    status = models.CharField("statut", max_length=20, choices=Order.Status.choices)
    note = models.CharField("commentaire", max_length=200, blank=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="auteur"
    )
    created_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "historique de commande"
        verbose_name_plural = "historique de commande"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.number} → {self.get_status_display()}"

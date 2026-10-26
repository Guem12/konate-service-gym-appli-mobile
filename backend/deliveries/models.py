from django.db import models

from core.models import TimeStampedModel


class Delivery(TimeStampedModel):
    class Status(models.TextChoices):
        TO_PREPARE = "to_prepare", "À préparer"
        IN_TRANSIT = "in_transit", "En cours"
        DELIVERED = "delivered", "Livrée"
        FAILED = "failed", "Échec"
        POSTPONED = "postponed", "Reportée"

    class FailureAction(models.TextChoices):
        NONE = "none", "Aucune action"
        RESTOCK = "restock", "Remettre en stock"
        KEEP_RESERVED = "keep_reserved", "Garder réservé"

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="delivery", verbose_name="commande"
    )
    status = models.CharField("statut", max_length=14, choices=Status.choices, default=Status.TO_PREPARE)
    courier_name = models.CharField("livreur", max_length=120, blank=True)
    slot = models.CharField("créneau", max_length=80, blank=True)
    address_text = models.CharField("adresse", max_length=255, blank=True)
    zone = models.CharField("quartier", max_length=80, blank=True)
    delivery_cost = models.PositiveIntegerField("coût réel (FCFA)", default=0)
    amount_collected = models.PositiveIntegerField("montant encaissé (FCFA)", default=0)
    cash_reconciled = models.BooleanField("espèces reversées à la boutique", default=False)
    delivered_at = models.DateTimeField("remise au client", null=True, blank=True)
    failure_action = models.CharField(
        "action en cas d'échec", max_length=14, choices=FailureAction.choices,
        default=FailureAction.NONE,
    )
    failure_reason = models.CharField("motif d'échec", max_length=200, blank=True)
    proof_note = models.CharField("preuve de livraison", max_length=200, blank=True)

    class Meta:
        verbose_name = "livraison"
        verbose_name_plural = "livraisons"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Livraison {self.order.number} — {self.get_status_display()}"

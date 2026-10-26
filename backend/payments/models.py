from django.db import models


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Espèces"
        ORANGE_MONEY = "orange_money", "Orange Money"
        TRANSFER = "transfer", "Virement"

    class Status(models.TextChoices):
        PENDING = "pending", "À vérifier"
        CONFIRMED = "confirmed", "Confirmé"
        REJECTED = "rejected", "Rejeté"

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="payments", verbose_name="commande"
    )
    method = models.CharField("moyen", max_length=20, choices=Method.choices)
    amount = models.PositiveIntegerField("montant", default=0)
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.PENDING)
    om_reference = models.CharField(
        "référence Orange Money", max_length=60, null=True, blank=True, unique=True
    )
    payer_phone = models.CharField("numéro du payeur", max_length=20, blank=True)
    screenshot = models.ImageField("capture d'écran", upload_to="payments/", blank=True, null=True)
    note = models.CharField("note", max_length=200, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payments_created", verbose_name="saisi par",
    )
    confirmed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payments_confirmed", verbose_name="confirmé par",
    )
    confirmed_at = models.DateTimeField("confirmé le", null=True, blank=True)
    rejected_reason = models.CharField("motif du rejet", max_length=200, blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "paiement"
        verbose_name_plural = "paiements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_method_display()} {self.amount} — {self.order.number}"

    def save(self, *args, **kwargs):
        if self.om_reference:
            self.om_reference = self.om_reference.strip().upper()
        else:
            self.om_reference = None
        super().save(*args, **kwargs)

from django.db import models

from core.models import TimeStampedModel


class Supplier(TimeStampedModel):
    name = models.CharField("nom", max_length=120)
    contact_name = models.CharField("contact", max_length=120, blank=True)
    phone = models.CharField("téléphone", max_length=30, blank=True)
    address = models.CharField("adresse", max_length=200, blank=True)
    products_supplied = models.CharField("produits fournis", max_length=255, blank=True)
    notes = models.TextField("notes", blank=True)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "fournisseur"
        verbose_name_plural = "fournisseurs"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockMovement(models.Model):
    class Type(models.TextChoices):
        IN = "in", "Entrée"
        SALE = "sale", "Vente"
        BREAKAGE = "breakage", "Casse"
        RETURN = "return", "Retour"
        ADJUSTMENT = "adjustment", "Correction"
        RESTOCK = "restock", "Réapprovisionnement"

    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.CASCADE, related_name="stock_movements",
        verbose_name="variante",
    )
    movement_type = models.CharField("type", max_length=12, choices=Type.choices)
    quantity = models.IntegerField("quantité (delta)")
    stock_after = models.IntegerField("stock après")
    reason = models.CharField("motif", max_length=200, blank=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stock_movements", verbose_name="utilisateur",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stock_movements", verbose_name="fournisseur",
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stock_movements", verbose_name="commande",
    )
    created_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "mouvement de stock"
        verbose_name_plural = "mouvements de stock"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["variant", "-created_at"])]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity:+d} — {self.variant}"

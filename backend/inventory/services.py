from django.db import transaction
from rest_framework.exceptions import ValidationError

from catalog.models import ProductVariant
from inventory.models import StockMovement


@transaction.atomic
def record_movement(
    variant_id,
    quantity,
    movement_type,
    user=None,
    reason="",
    order=None,
    supplier=None,
):
    """Applique un delta de stock et trace le mouvement.

    `quantity` est signé : négatif pour une sortie (vente, casse), positif pour
    une entrée. La ligne de variante est verrouillée (select_for_update) pour
    empêcher la vente du même dernier exemplaire par deux requêtes concurrentes.
    """
    variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
    new_stock = variant.stock_qty + quantity
    if new_stock < 0:
        raise ValidationError(
            {"detail": f"Stock insuffisant pour « {variant.product.name} — {variant.label} »."}
        )
    variant.stock_qty = new_stock
    variant.save(update_fields=["stock_qty", "updated_at"])
    return StockMovement.objects.create(
        variant=variant,
        quantity=quantity,
        stock_after=new_stock,
        movement_type=movement_type,
        reason=reason[:200],
        user=user,
        order=order,
        supplier=supplier,
    )

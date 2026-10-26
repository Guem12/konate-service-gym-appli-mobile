from urllib.parse import quote

from .models import ShopSetting


def normalize_phone(raw, default_country="223"):
    """Normalise un numéro malien au format international sans '+' (223XXXXXXXX)."""
    if not raw:
        return ""
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith(default_country) and len(digits) == len(default_country) + 8:
        return digits
    if len(digits) == 8:
        return f"{default_country}{digits}"
    return digits


def whatsapp_link(phone, message=""):
    """Construit un lien wa.me avec message prérempli (aucune API WhatsApp)."""
    number = normalize_phone(phone)
    text = quote(message or "", safe="")
    return f"https://wa.me/{number}" + (f"?text={text}" if text else "")


def product_whatsapp_message(product, variant=None):
    setting = ShopSetting.load()
    if variant is not None:
        price = variant.price_sale
    else:
        price = product.min_price
    try:
        return setting.whatsapp_product_template.format(
            product=product.name + (f" — {variant.label}" if variant else ""),
            price=f"{price:,} FCFA".replace(",", " "),
        )
    except (KeyError, IndexError):
        return f"Bonjour, je suis intéressé(e) par {product.name}."


def order_whatsapp_message(order):
    setting = ShopSetting.load()
    try:
        return setting.whatsapp_order_template.format(
            order_number=order.number,
            total=f"{order.total:,} FCFA".replace(",", " "),
        )
    except (KeyError, IndexError):
        return f"Bonjour, je souhaite discuter de ma commande {order.number}."

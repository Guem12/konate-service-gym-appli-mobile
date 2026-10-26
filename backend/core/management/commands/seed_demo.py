"""Jeu de données initial : boutique, catalogue, comptes et commandes de démo.

Usage : python manage.py seed_demo
Idempotent : relancer la commande ne duplique pas les données.
"""
import datetime as dt
import io
from pathlib import Path

import pyotp
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from accounts.models import Address, User
from catalog.models import Brand, Category, Coupon, Product, ProductImage, ProductVariant, Promotion
from core.models import ShopSetting
from orders.models import Order
from orders.services import create_order
from payments.models import Payment

OWNER_SECRET = "JBSWY3DPEHPK3PXP"
COLORS = {
    "Musculation": ("#111827", "#f5b301"),
    "Bancs et supports": ("#1f2937", "#38bdf8"),
    "Machines": ("#0f172a", "#a3e635"),
    "Cardio": ("#111827", "#fb7185"),
    "Accessoires": ("#1c1917", "#fbbf24"),
}

PRODUCTS = [
    # (nom, catégorie, marque, description, [variantes (label, achat, vente, stock)], en avant, nouveau, garantie mois)
    ("Haltères hexagonaux", "Musculation", "IronPro",
     "Haltères en fonte gainée de caoutchouc, facettes hexagonales anti-roulement. "
     "Idéals pour la musculation à domicile et les salles de sport.",
     [("10 kg", 18000, 28000, 12), ("20 kg", 32000, 48000, 8), ("30 kg", 48000, 72000, 4)], True, True, 12),
    ("Disques olympiques", "Musculation", "IronPro",
     "Disques en fonte avec revêtement caoutchouc, diamètre 50 mm. Compatibles barres olympiques.",
     [("5 kg", 8000, 14000, 20), ("10 kg", 15000, 25000, 16), ("20 kg", 30000, 48000, 10)], False, False, 0),
    ("Barre olympique 2 m", "Musculation", "IronPro",
     "Barre olympique 2 m, charge maximale 300 kg, roulements à billes, gravures antidérapantes.",
     [("20 kg", 65000, 95000, 6)], True, False, 12),
    ("Banc de musculation inclinable", "Bancs et supports", "FitLine",
     "Banc multi-positions (plat, incliné, décliné), structure acier renforcée, "
     "dossier rembourré et repose-barres réglable.",
     [("Standard", 95000, 150000, 5)], True, True, 12),
    ("Rack squat", "Bancs et supports", "FitLine",
     "Cage à squat avec barres de sécurité réglables, crochets J et barre de traction.",
     [("Standard", 220000, 350000, 3)], False, False, 12),
    ("Banc romain", "Bancs et supports", "FitLine",
     "Banc romain pour le développement des lombaires et des ischio-jambiers.",
     [("Standard", 85000, 135000, 4)], False, False, 6),
    ("Presse à cuisses", "Machines", "GymTech",
     "Presse à cuisses guidée 45°, assise confortable, plaques de charge jusqu'à 200 kg.",
     [("Standard", 850000, 1250000, 2)], True, False, 24),
    ("Machine poulie haute", "Machines", "GymTech",
     "Station de tirage vertical avec plusieurs poignées, poulie de qualité professionnelle.",
     [("Standard", 620000, 950000, 2)], False, True, 24),
    ("Smith machine", "Machines", "GymTech",
     "Machine à barre guidée avec crochets de sécurité, idéale pour la musculation encadrée.",
     [("Standard", 780000, 1150000, 1)], False, False, 24),
    ("Tapis de course", "Cardio", "CardioMax",
     "Tapis de course pliable, moteur 2,5 CV, 12 programmes, écran LCD, "
     "vitesse jusqu'à 16 km/h.",
     [("T500", 450000, 650000, 3), ("T700", 620000, 890000, 2)], True, False, 24),
    ("Vélo d'appui", "Cardio", "CardioMax",
     "Vélo de salle avec résistance magnétique, selle réglable et ordinateur de bord.",
     [("Standard", 320000, 480000, 4)], False, True, 12),
    ("Rameur", "Cardio", "CardioMax",
     "Rameur à résistance magnétique, suivi de la dépense calorique et des mouvements.",
     [("Standard", 380000, 550000, 3)], False, False, 12),
    ("Kettlebell", "Accessoires", "IronPro",
     "Kettlebell en fonte avec poignée large, parfait pour le cross-training.",
     [("8 kg", 9000, 16000, 15), ("16 kg", 18000, 28000, 10), ("24 kg", 26000, 40000, 6)], False, False, 0),
    ("Corde à sauter", "Accessoires", "FitLine",
     "Corde à sauter avec câble réglable et poignées antidérapantes.",
     [("Standard", 2500, 5000, 30)], False, True, 0),
    ("Ceinture de force", "Accessoires", "FitLine",
     "Ceinture lombaire en cuir, maintien renforcé pour les charges lourdes.",
     [("M", 12000, 22000, 8), ("L", 12000, 22000, 8)], False, False, 0),
    ("Tapis de sol fitness", "Accessoires", "FitLine",
     "Tapis de sol antidérapant 10 mm, facile à rouler et à transporter.",
     [("Bleu", 6000, 12000, 20), ("Noir", 6000, 12000, 18)], False, False, 0),
]


def _font(size):
    for path in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_image(title, category, path, size=(900, 900), banner=False):
    bg, accent = COLORS.get(category, ("#111827", "#f5b301"))
    width, height = (1200, 500) if banner else size
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    for i in range(height):
        ratio = i / max(1, height)
        color = tuple(
            int(int(bg.lstrip("#")[j:j + 2], 16) * (1 - ratio * 0.35)
                + int(accent.lstrip("#")[j:j + 2], 16) * (ratio * 0.12))
            for j in (0, 2, 4)
        )
        draw.line([(0, i), (width, i)], fill=color)
    draw.ellipse(
        [width * 0.62, -height * 0.35, width * 1.25, height * 0.75],
        fill=accent,
    )
    draw.rectangle([0, height - 18, width, height], fill=accent)
    font_big = _font(54 if not banner else 66)
    font_small = _font(26 if not banner else 30)
    draw.text((60, height * 0.30), "KONATÉ", font=font_small, fill="#ffffff")
    draw.text((60, height * 0.38), "SERVICE GYM", font=font_small, fill=accent)

    words = title.split()
    lines, line = [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > (16 if not banner else 24):
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    y = height * 0.56 if not banner else height * 0.52
    for text in lines:
        draw.text((60, y), text, font=font_big, fill="#ffffff")
        y += (70 if not banner else 78)

    image.save(path, "JPEG", quality=88)
    return path


class Command(BaseCommand):
    help = "Crée le jeu de données de démonstration (catalogue, comptes, commandes)."

    def handle(self, *args, **options):
        media = Path("media")
        (media / "products").mkdir(parents=True, exist_ok=True)
        (media / "banners").mkdir(parents=True, exist_ok=True)

        shop = ShopSetting.load()
        shop.shop_name = "Konaté Service Gym"
        shop.whatsapp_phone = "22370000001"
        shop.orange_money_phone = "22370000002"
        shop.phone = "+223 70 00 00 01"
        shop.email = "contact@konate-service-gym.ml"
        shop.address = "Hamdallaye ACI 2000, Bamako, Mali"
        shop.opening_hours = "Lun-Sam : 08h00 - 20h00"
        shop.delivery_note = "Livraison gratuite à Bamako"
        shop.delivery_zones = ["Hamdallaye", "Badalabougou", "Korofina", "Faladié", "Sotuba", "Niamakoro"]
        shop.delivery_slots = ["Matin (08h-12h)", "Après-midi (14h-17h)", "Soir (17h-20h)"]
        shop.return_delay_days = 7
        shop.save()
        self.stdout.write("Boutique configurée.")

        owner, created = User.objects.get_or_create(
            phone="22370000001",
            defaults={"full_name": "Mamadou Konaté", "role": User.Role.OWNER, "email": "contact@konate-service-gym.ml"},
        )
        # Le jeu de démonstration est rejoué souvent : on réinitialise toujours
        # les identifiants affichés pour qu'ils restent valides.
        owner.set_password("Owner@2026")
        owner.totp_secret = OWNER_SECRET
        owner.two_factor_enabled = True
        owner.is_staff = True
        owner.save()

        vendor, created = User.objects.get_or_create(
            phone="22370000003",
            defaults={"full_name": "Fatoumata Traoré", "role": User.Role.VENDOR},
        )
        vendor.set_password("Vendeur@2026")
        vendor.save()

        client, created = User.objects.get_or_create(
            phone="22370000002",
            defaults={"full_name": "Awa Diallo", "role": User.Role.CLIENT},
        )
        client.set_password("Client@2026")
        client.save()
        client2, created = User.objects.get_or_create(
            phone="22370000004",
            defaults={"full_name": "Ibrahim Coulibaly", "role": User.Role.CLIENT},
        )
        client2.set_password("Client@2026")
        client2.save()

        Address.objects.get_or_create(
            user=client, label="Domicile",
            defaults={
                "district": "Hamdallaye ACI 2000", "street": "Rue 512, porte 48",
                "landmark": "En face de la pharmacie Sacré-Cœur", "phone": client.phone,
                "is_default": True,
            },
        )
        Address.objects.get_or_create(
            user=client2, label="Bureau",
            defaults={
                "district": "Badalabougou", "street": "Rue 224",
                "landmark": "À côté de la station Total", "phone": client2.phone,
                "is_default": True,
            },
        )

        categories = {}
        for index, name in enumerate(["Musculation", "Bancs et supports", "Machines", "Cardio", "Accessoires"]):
            category, _ = Category.objects.get_or_create(
                name=name, defaults={"order": index, "description": f"Équipement {name.lower()} professionnel"}
            )
            categories[name] = category

        brands = {}
        for name in ["IronPro", "FitLine", "GymTech", "CardioMax"]:
            brand, _ = Brand.objects.get_or_create(name=name)
            brands[name] = brand

        created_products = []
        for index, (name, category_name, brand_name, description, variants, featured, is_new, warranty) in enumerate(PRODUCTS):
            category = categories[category_name]
            brand = brands[brand_name]
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": category,
                    "brand": brand,
                    "description": description,
                    "characteristics": "\n".join(
                        [
                            "Structure acier renforcée" if category_name in {"Machines", "Bancs et supports"} else "Matériel professionnel",
                            "Garantie boutique Konaté Service Gym",
                            "Livraison gratuite à Bamako",
                            "Paiement Orange Money accepté",
                        ]
                    ),
                    "warranty_months": warranty,
                    "is_featured": featured,
                    "is_new": is_new,
                },
            )
            product.category = category
            product.brand = brand
            product.description = description
            product.is_featured = featured
            product.is_new = is_new
            product.warranty_months = warranty
            product.save()

            for index_variant, (label, purchase, sale, stock) in enumerate(variants):
                sku = f"KSG-{index + 1:03d}-{index_variant + 1}"
                ProductVariant.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "product": product, "label": label, "price_purchase": purchase,
                        "price_sale": sale, "stock_qty": stock, "low_stock_threshold": 3,
                        "attributes": {"poids" if "kg" in label else "modèle": label},
                    },
                )

            if not product.images.exists():
                file_path = media / "products" / f"{product.slug}.jpg"
                make_image(product.name, category_name, file_path)
                with open(file_path, "rb") as handle:
                    ProductImage.objects.create(
                        product=product,
                        image=ContentFile(handle.read(), name=f"{product.slug}.jpg"),
                        alt=product.name,
                        is_primary=True,
                    )
            created_products.append(product)

        promotion, _ = Promotion.objects.get_or_create(
            name="Rentrée fitness -10%",
            defaults={
                "discount_type": Promotion.DiscountType.PERCENTAGE,
                "value": 10,
                "end_at": timezone.now() + dt.timedelta(days=30),
                "show_on_home": True,
                "banner_title": "Équipez-vous pour la rentrée",
                "banner_subtitle": "-10% sur une sélection de matériel de musculation",
            },
        )
        promotion.products.set(created_products[:6])
        if not promotion.banner_image:
            banner_path = media / "banners" / "rentree-2026.jpg"
            make_image("Rentrée fitness -10%", "Musculation", banner_path, banner=True)
            with open(banner_path, "rb") as handle:
                promotion.banner_image.save(
                    "rentree-2026.jpg", ContentFile(handle.read()), save=True
                )

        Coupon.objects.get_or_create(
            code="BIENVENUE10",
            defaults={
                "discount_type": Coupon.DiscountType.PERCENTAGE,
                "value": 10,
                "min_purchase": 20000,
                "max_uses": 100,
                "valid_until": timezone.now() + dt.timedelta(days=90),
            },
        )
        Coupon.objects.get_or_create(
            code="LIVRAISON5000",
            defaults={
                "discount_type": Coupon.DiscountType.FIXED,
                "value": 5000,
                "min_purchase": 50000,
                "max_uses": 50,
                "valid_until": timezone.now() + dt.timedelta(days=60),
            },
        )

        if not Order.objects.exists():
            self._demo_orders(client, client2, created_products)

        self.stdout.write(self.style.SUCCESS("Jeu de données prêt."))
        self.stdout.write("")
        self.stdout.write("Comptes de démonstration :")
        self.stdout.write("  Propriétaire : 70 00 00 01 / Owner@2026 (2FA active)")
        self.stdout.write(f"    Secret TOTP : {OWNER_SECRET}")
        self.stdout.write(f"    Code actuel : {pyotp.TOTP(OWNER_SECRET).now()}")
        self.stdout.write("  Vendeur      : 70 00 00 03 / Vendeur@2026")
        self.stdout.write("  Client       : 70 00 00 02 / Client@2026")
        self.stdout.write("  Client 2     : 70 00 00 04 / Client@2026")
        self.stdout.write("  WhatsApp boutique : +223 70 00 00 01")
        self.stdout.write("  Orange Money      : +223 70 00 00 02")

    def _demo_orders(self, client, client2, products):
        address = client.addresses.first()
        address2 = client2.addresses.first()

        def variant(product, index=0):
            return product.variants.all()[index]

        specs = [
            (client, address, [("Haltères hexagonaux", 1, 1), ("Tapis de sol fitness", 0, 2)], "delivered", 12, "orange_money"),
            (client2, address2, [("Tapis de course", 0, 1)], "preparing", 5, "orange_money"),
            (client, address, [("Barre olympique 2 m", 0, 1), ("Disques olympiques", 2, 2)], "pending_payment", 1, "orange_money"),
            (client2, address2, [("Kettlebell", 1, 2), ("Corde à sauter", 0, 1)], "delivered", 8, "cash"),
            (client, address, [("Banc de musculation inclinable", 0, 1)], "confirmed", 3, "cash"),
        ]
        sequence = 1000
        for customer, addr, lines, final_status, days_ago, method in specs:
            items = []
            for name, variant_index, quantity in lines:
                product = next(p for p in products if p.name == name)
                items.append({"variant": variant(product, variant_index).id, "quantity": quantity})
            sequence += 1
            om_reference = f"OM2026{sequence}" if method == "orange_money" else ""
            order, _ = create_order(
                user=customer,
                items=items,
                fulfillment=Order.Fulfillment.DELIVERY,
                address=addr,
                channel=Order.Channel.APP if method == "orange_money" else Order.Channel.COUNTER,
                payment_method=method,
                payment_reference=om_reference,
                delivery_slot="Matin (08h-12h)",
                client_reference=None,
                created_by=None,
            )
            created_at = timezone.now() - dt.timedelta(days=days_ago)
            Order.objects.filter(pk=order.pk).update(created_at=created_at, updated_at=created_at)
            if method == "orange_money":
                payment = order.payments.first()
                if final_status in {"preparing", "delivered"} and payment:
                    payment.status = Payment.Status.CONFIRMED
                    payment.confirmed_at = created_at
                    payment.confirmed_by = User.objects.filter(role="owner").first()
                    payment.save()
                    order.amount_paid = order.total
                    order.balance_due = 0
                    order.save()
            if final_status in {"preparing", "delivered"}:
                order.status = final_status
                order.save(update_fields=["status"])
                if final_status == "delivered":
                    order.delivered_at = created_at
                    order.save(update_fields=["delivered_at"])
                    from deliveries.models import Delivery

                    Delivery.objects.filter(order=order).update(
                        status="delivered", delivered_at=created_at,
                        courier_name="Moussa", delivery_cost=2500,
                        amount_collected=order.total, cash_reconciled=True,
                    )
            else:
                order.status = final_status
                order.save(update_fields=["status"])
                if final_status == "pending_payment":
                    order.created_at = timezone.now() - dt.timedelta(days=2)
                    order.save(update_fields=["created_at"])

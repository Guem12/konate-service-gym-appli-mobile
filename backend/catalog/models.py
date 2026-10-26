from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField("nom", max_length=80)
    slug = models.SlugField("slug", max_length=90, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True, blank=True,
        verbose_name="catégorie parente",
    )
    image = models.ImageField("image", upload_to="categories/", blank=True, null=True)
    description = models.CharField("description", max_length=255, blank=True)
    order = models.PositiveIntegerField("ordre d'affichage", default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:80] or "categorie"
            slug = base
            index = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                index += 1
                slug = f"{base}-{index}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def product_count(self):
        # Si une annotation Django existe
        cached = getattr(self, "_product_count", None)
        if cached is not None:
            return cached
        # La vue d'accueil annote "published_count" pour éviter une requête par catégorie.
        cached = getattr(self, "published_count", None)
        if cached is not None:
            return cached
        return self.products.filter(status=Product.Status.PUBLISHED).count()

    @product_count.setter
    def product_count(self, value):
        self._product_count = value


class Brand(TimeStampedModel):
    name = models.CharField("nom", max_length=80, unique=True)
    slug = models.SlugField("slug", max_length=90, unique=True, blank=True)
    logo = models.ImageField("logo", upload_to="brands/", blank=True, null=True)

    class Meta:
        verbose_name = "marque"
        verbose_name_plural = "marques"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:90] or "marque"
        super().save(*args, **kwargs)


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Publié"
        DRAFT = "draft", "Brouillon"
        HIDDEN = "hidden", "Masqué"

    name = models.CharField("nom", max_length=160)
    slug = models.SlugField("slug", max_length=170, unique=True, blank=True)
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products",
        verbose_name="marque",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products", verbose_name="catégorie"
    )
    description = models.TextField("description", blank=True)
    characteristics = models.TextField(
        "caractéristiques", blank=True, help_text="Une caractéristique par ligne"
    )
    warranty_months = models.PositiveIntegerField("garantie (mois)", default=0)
    status = models.CharField("état", max_length=12, choices=Status.choices, default=Status.PUBLISHED)
    is_featured = models.BooleanField("mis en avant", default=False)
    is_new = models.BooleanField("nouveauté", default=False)
    sold_count = models.PositiveIntegerField("vendu (cache)", default=0, editable=False)

    class Meta:
        verbose_name = "produit"
        verbose_name_plural = "produits"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"]), models.Index(fields=["name"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or "produit"
            slug = base
            index = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                index += 1
                slug = f"{base}-{index}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def default_variant(self):
        return self.variants.filter(is_active=True).order_by("price_sale").first()

    @property
    def min_price(self):
        prices = [v.price_sale for v in self.variants.all() if v.is_active]
        return min(prices) if prices else 0

    @property
    def total_stock(self):
        return sum(v.stock_qty for v in self.variants.all() if v.is_active)

    @property
    def active_promotion(self):
        now = timezone.now()
        cache = getattr(self, "_prefetched_objects_cache", {}).get("promotions")
        promos = list(cache) if cache is not None else list(self.promotions.all())
        running = [p for p in promos if p.is_active and p.start_at <= now <= p.end_at]
        return max(running, key=lambda p: p.value) if running else None


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants", verbose_name="produit"
    )
    label = models.CharField(
        "libellé", max_length=80, help_text="Ex. 20 kg, rouge, 120 × 60 cm"
    )
    attributes = models.JSONField(
        "attributs", default=dict, blank=True,
        help_text='Ex. {"poids": "20 kg", "couleur": "noir"}',
    )
    sku = models.CharField("SKU", max_length=60, unique=True)
    barcode = models.CharField("code-barres", max_length=60, blank=True)
    price_purchase = models.PositiveIntegerField(
        "prix d'achat (FCFA)", default=0, validators=[MinValueValidator(0)]
    )
    price_sale = models.PositiveIntegerField(
        "prix de vente (FCFA)", validators=[MinValueValidator(0)]
    )
    stock_qty = models.IntegerField("stock", default=0)
    low_stock_threshold = models.PositiveIntegerField("seuil d'alerte", default=3)
    weight_grams = models.PositiveIntegerField("poids (g)", default=0, blank=True)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "variante"
        verbose_name_plural = "variantes"
        ordering = ["product", "price_sale"]

    def __str__(self):
        return f"{self.product.name} — {self.label}"

    @property
    def stock_status(self):
        if self.stock_qty <= 0:
            return "out_of_stock"
        if self.stock_qty <= self.low_stock_threshold:
            return "low_stock"
        return "in_stock"

    @property
    def margin(self):
        return self.price_sale - self.price_purchase


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="produit"
    )
    image = models.ImageField("image", upload_to="products/")
    alt = models.CharField("texte alternatif", max_length=120, blank=True)
    is_primary = models.BooleanField("image principale", default=False)
    order = models.PositiveIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "photo produit"
        verbose_name_plural = "photos produit"
        ordering = ["order", "id"]


class Favorite(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="favorites", verbose_name="client"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="favorites", verbose_name="produit"
    )
    created_at = models.DateTimeField("ajouté le", auto_now_add=True)

    class Meta:
        verbose_name = "favori"
        verbose_name_plural = "favoris"
        unique_together = ("user", "product")


class Promotion(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Pourcentage"
        FIXED = "fixed", "Montant fixe"

    name = models.CharField("nom", max_length=120)
    discount_type = models.CharField("type", max_length=12, choices=DiscountType.choices)
    value = models.PositiveIntegerField("valeur", help_text="% ou montant FCFA")
    start_at = models.DateTimeField("début", default=timezone.now)
    end_at = models.DateTimeField("fin")
    products = models.ManyToManyField(Product, related_name="promotions", blank=True, verbose_name="produits")
    categories = models.ManyToManyField(Category, related_name="promotions", blank=True, verbose_name="catégories")
    is_active = models.BooleanField("active", default=True)
    show_on_home = models.BooleanField("bannière d'accueil", default=False)
    banner_image = models.ImageField("image bannière", upload_to="banners/", blank=True, null=True)
    banner_title = models.CharField("titre bannière", max_length=100, blank=True)
    banner_subtitle = models.CharField("sous-titre bannière", max_length=160, blank=True)

    class Meta:
        verbose_name = "promotion"
        verbose_name_plural = "promotions"
        ordering = ["-start_at"]

    def __str__(self):
        return self.name

    @property
    def is_running(self):
        now = timezone.now()
        return self.is_active and self.start_at <= now <= self.end_at

    def discount_for(self, price):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return min(price, round(price * self.value / 100))
        return min(price, self.value)


class Coupon(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Pourcentage"
        FIXED = "fixed", "Montant fixe"

    code = models.CharField("code", max_length=30, unique=True)
    discount_type = models.CharField("type", max_length=12, choices=DiscountType.choices)
    value = models.PositiveIntegerField("valeur", help_text="% ou montant FCFA")
    min_purchase = models.PositiveIntegerField("achat minimum (FCFA)", default=0)
    max_uses = models.PositiveIntegerField("utilisations max", default=0, help_text="0 = illimité")
    used_count = models.PositiveIntegerField("utilisations", default=0)
    valid_from = models.DateTimeField("valide du", default=timezone.now)
    valid_until = models.DateTimeField("valide jusqu'au", null=True, blank=True)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "code promo"
        verbose_name_plural = "codes promo"
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def validate_for(self, subtotal):
        now = timezone.now()
        if not self.is_active:
            raise ValueError("Ce code promo n'est plus actif.")
        if self.valid_from > now:
            raise ValueError("Ce code promo n'est pas encore valable.")
        if self.valid_until and self.valid_until < now:
            raise ValueError("Ce code promo a expiré.")
        if self.max_uses and self.used_count >= self.max_uses:
            raise ValueError("Ce code promo a atteint sa limite d'utilisation.")
        if subtotal < self.min_purchase:
            raise ValueError(
                f"Ce code promo s'applique à partir de {self.min_purchase:,} FCFA.".replace(",", " ")
            )
        return self.discount_for(subtotal)

    def discount_for(self, subtotal):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return min(subtotal, round(subtotal * self.value / 100))
        return min(subtotal, self.value)

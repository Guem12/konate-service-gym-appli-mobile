from django.db.models import Count, Min, Q, Sum
from rest_framework import serializers

from catalog.models import (
    Brand,
    Category,
    Coupon,
    Favorite,
    Product,
    ProductImage,
    ProductVariant,
    Promotion,
)


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    children = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "parent", "image", "image_url", "description",
            "order", "is_active", "product_count", "children",
        ]
        extra_kwargs = {"image": {"write_only": True, "required": False}}

    def get_product_count(self, obj):
        return getattr(obj, "product_count", obj.products.filter(status=Product.Status.PUBLISHED).count())

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True, context=self.context).data

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo"]


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "url", "alt", "is_primary", "order"]
        extra_kwargs = {"image": {"write_only": True, "required": False}}

    def get_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class ProductVariantSerializer(serializers.ModelSerializer):
    stock_status = serializers.ReadOnlyField()
    margin = serializers.ReadOnlyField()

    class Meta:
        model = ProductVariant
        fields = [
            "id", "label", "attributes", "sku", "barcode", "price_purchase",
            "price_sale", "stock_qty", "low_stock_threshold", "stock_status",
            "margin", "is_active",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    compare_price = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default="")
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "category", "category_name", "brand_name", "price",
            "compare_price", "primary_image", "stock_status", "is_featured", "is_new",
            "warranty_months", "sold_count", "is_favorite",
        ]

    def _variants(self, obj):
        return [v for v in obj.variants.all() if v.is_active]

    def get_price(self, obj):
        prices = [v.price_sale for v in self._variants(obj)]
        return min(prices) if prices else 0

    def get_compare_price(self, obj):
        if not obj.active_promotion:
            return None
        price = self.get_price(obj)
        return max(price, price + obj.active_promotion.discount_for(price))

    def get_primary_image(self, obj):
        images = list(obj.images.all())
        image = next((img for img in images if img.is_primary), images[0] if images else None)
        if not image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(image.image.url) if request else image.image.url

    def get_stock_status(self, obj):
        variants = self._variants(obj)
        if not variants or sum(v.stock_qty for v in variants) <= 0:
            return "out_of_stock"
        if any(v.stock_qty <= v.low_stock_threshold for v in variants):
            return "low_stock"
        return "in_stock"

    def get_is_favorite(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.pk in self.context.get("favorite_ids", set())


class ProductDetailSerializer(ProductListSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    category_detail = CategorySerializer(source="category", read_only=True)
    brand_detail = BrandSerializer(source="brand", read_only=True)
    characteristics_list = serializers.SerializerMethodField()
    description_lines = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description", "characteristics", "characteristics_list", "description_lines",
            "variants", "images", "category_detail", "brand_detail", "status", "is_favorite",
        ]

    def get_characteristics_list(self, obj):
        return [line.strip() for line in (obj.characteristics or "").splitlines() if line.strip()]

    def get_description_lines(self, obj):
        return [p.strip() for p in (obj.description or "").split("\n") if p.strip()]


class AdminVariantWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProductVariant
        fields = [
            "id", "label", "attributes", "sku", "barcode", "price_purchase",
            "price_sale", "stock_qty", "low_stock_threshold", "is_active",
        ]
        extra_kwargs = {"sku": {"validators": [], "required": False}}


class AdminImageWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt", "is_primary", "order"]


class AdminProductSerializer(serializers.ModelSerializer):
    variants = AdminVariantWriteSerializer(many=True)
    images = AdminImageWriteSerializer(many=True, required=False)
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default="")
    total_stock = serializers.ReadOnlyField()
    price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "brand", "brand_name", "category", "category_name",
            "description", "characteristics", "warranty_months", "status", "is_featured",
            "is_new", "variants", "images", "total_stock", "price", "sold_count", "created_at",
        ]
        read_only_fields = ["slug", "sold_count", "created_at"]

    def get_price(self, obj):
        prices = [v.price_sale for v in obj.variants.all()]
        return min(prices) if prices else 0

    def validate_variants(self, value):
        if not value:
            raise serializers.ValidationError("Ajoutez au moins une variante (prix et stock).")
        skus = [v.get("sku") for v in value if v.get("sku")]
        if len(skus) != len(set(skus)):
            raise serializers.ValidationError("Les SKU doivent être uniques.")
        return value

    def _sync_variants(self, product, variants):
        existing = {v.pk: v for v in product.variants.all()}
        kept = set()
        for item in variants:
            variant_id = item.pop("id", None)
            sku = item.get("sku")
            if sku:
                duplicate = ProductVariant.objects.filter(sku=sku)
                if variant_id:
                    duplicate = duplicate.exclude(pk=variant_id)
                if duplicate.exists():
                    raise serializers.ValidationError(
                        {"variants": f"Le SKU « {sku} » est déjà utilisé par un autre article."}
                    )
            if variant_id and variant_id in existing:
                variant = existing[variant_id]
                for field, val in item.items():
                    setattr(variant, field, val)
                variant.save()
                kept.add(variant.pk)
            else:
                created = ProductVariant.objects.create(product=product, **item)
                kept.add(created.pk)
        product.variants.exclude(pk__in=kept).update(is_active=False)

    @staticmethod
    def _sync_images(product, images):
        for index, item in enumerate(images):
            image_id = item.pop("id", None)
            if image_id:
                ProductImage.objects.filter(pk=image_id, product=product).update(**item)
            elif item.get("image"):
                ProductImage.objects.create(product=product, order=index, **item)

    def create(self, validated_data):
        variants = validated_data.pop("variants", [])
        images = validated_data.pop("images", [])
        product = Product.objects.create(**validated_data)
        self._sync_variants(product, variants)
        self._sync_images(product, images)
        return product

    def update(self, instance, validated_data):
        variants = validated_data.pop("variants", None)
        images = validated_data.pop("images", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if variants is not None:
            self._sync_variants(instance, variants)
        if images:
            self._sync_images(instance, images)
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source="product", read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "product", "product_detail", "created_at"]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        favorite, _ = Favorite.objects.get_or_create(
            user=self.context["request"].user, product=validated_data["product"]
        )
        return favorite


class PromotionSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    banner_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id", "name", "discount_type", "value", "start_at", "end_at", "products",
            "categories", "is_active", "show_on_home", "banner_image", "banner_image_url",
            "banner_title", "banner_subtitle", "product_count",
        ]
        extra_kwargs = {"banner_image": {"write_only": True, "required": False}}

    def get_product_count(self, obj):
        return obj.products.count()

    def get_banner_image_url(self, obj):
        if not obj.banner_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.banner_image.url) if request else obj.banner_image.url

    def validate(self, attrs):
        if attrs.get("discount_type") == Promotion.DiscountType.PERCENTAGE and attrs.get("value", 0) > 100:
            raise serializers.ValidationError({"value": "Un pourcentage ne peut pas dépasser 100."})
        if attrs.get("start_at") and attrs.get("end_at") and attrs["start_at"] >= attrs["end_at"]:
            raise serializers.ValidationError({"end_at": "La date de fin doit suivre la date de début."})
        return attrs


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id", "code", "discount_type", "value", "min_purchase", "max_uses",
            "used_count", "valid_from", "valid_until", "is_active",
        ]
        read_only_fields = ["used_count"]

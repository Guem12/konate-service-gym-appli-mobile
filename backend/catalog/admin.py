from django.contrib import admin

from catalog.models import Brand, Category, Coupon, Favorite, Product, ProductImage, ProductVariant, Promotion


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("label", "sku", "barcode", "price_purchase", "price_sale", "stock_qty", "low_stock_threshold", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "status", "is_featured", "total_stock")
    list_filter = ("status", "category", "brand", "is_featured", "is_new")
    search_fields = ("name", "variants__sku", "variants__barcode")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductImageInline]

    @admin.display(description="stock")
    def total_stock(self, obj):
        return obj.total_stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "order", "is_active")
    list_filter = ("is_active", "parent")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("name", "discount_type", "value", "start_at", "end_at", "is_active", "show_on_home")
    list_filter = ("is_active", "discount_type", "show_on_home")
    filter_horizontal = ("products", "categories")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "max_uses", "used_count", "is_active", "valid_until")
    search_fields = ("code",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "label", "price_sale", "stock_qty", "is_active")
    search_fields = ("sku", "barcode", "product__name")
    list_filter = ("is_active",)

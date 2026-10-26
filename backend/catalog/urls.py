from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.views import (
    AdminBrandViewSet,
    AdminCategoryViewSet,
    AdminCouponViewSet,
    AdminProductViewSet,
    AdminPromotionViewSet,
    BrandViewSet,
    CategoryViewSet,
    FavoriteViewSet,
    HomeView,
    ProductViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register("categories", CategoryViewSet, basename="category")
router.register("brands", BrandViewSet, basename="brand")
router.register("products", ProductViewSet, basename="product")
router.register("me/favorites", FavoriteViewSet, basename="favorite")
router.register("home", HomeView, basename="home")
router.register("admin/products", AdminProductViewSet, basename="admin-product")
router.register("admin/categories", AdminCategoryViewSet, basename="admin-category")
router.register("admin/brands", AdminBrandViewSet, basename="admin-brand")
router.register("admin/promotions", AdminPromotionViewSet, basename="admin-promotion")
router.register("admin/coupons", AdminCouponViewSet, basename="admin-coupon")

urlpatterns = [path("", include(router.urls))]

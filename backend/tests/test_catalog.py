import pytest

from catalog.models import Product
from tests.conftest import login

pytestmark = pytest.mark.django_db


def test_public_catalog_only_published(api, catalog):
    Product.objects.create(
        name="Brouillon", category=catalog["category"], status=Product.Status.DRAFT
    )
    response = api.get("/api/v1/products")
    assert response.status_code == 200
    names = [item["name"] for item in response.data["results"]]
    assert "Haltères hexagonaux" in names
    assert "Brouillon" not in names


def test_product_detail_and_search(api, catalog):
    detail = api.get(f"/api/v1/products/{catalog['product'].slug}")
    assert detail.status_code == 200
    assert detail.data["price"] == 28000
    assert len(detail.data["variants"]) == 2
    assert detail.data["stock_status"] in {"in_stock", "low_stock"}

    results = api.get("/api/v1/products/search?q=haltères")
    assert results.status_code == 200
    assert results.data["results"][0]["name"] == "Haltères hexagonaux"


def test_filter_by_category_and_price(api, catalog):
    response = api.get(f"/api/v1/products?category={catalog['category'].slug}&price_max=30000")
    names = [item["name"] for item in response.data["results"]]
    assert "Haltères hexagonaux" in names
    assert "Tapis de course" not in names


def test_home_returns_sections(api, catalog):
    response = api.get("/api/v1/home")
    assert response.status_code == 200
    for key in ("banners", "categories", "popular", "new", "promotions", "featured"):
        assert key in response.data


def test_favorites_toggle(api, catalog, client_user, shop):
    login(api, client_user.phone, "Client@2026")
    response = api.post("/api/v1/me/favorites/toggle", {"product": catalog["product"].id}, format="json")
    assert response.status_code == 201
    assert response.data["is_favorite"] is True
    listing = api.get("/api/v1/me/favorites")
    assert len(listing.data) == 1
    response = api.post("/api/v1/me/favorites/toggle", {"product": catalog["product"].id}, format="json")
    assert response.data["is_favorite"] is False


def test_whatsapp_link_prefilled(api, shop, catalog):
    response = api.get(f"/api/v1/whatsapp/link?product={catalog['product'].id}")
    assert response.status_code == 200
    assert response.data["url"].startswith("https://wa.me/22370000001?text=")
    assert "Halt%C3%A8res" in response.data["url"]


def test_delivery_settings_public(api, shop):
    response = api.get("/api/v1/settings")
    assert response.status_code == 200
    assert response.data["whatsapp_phone"] == "22370000001"
    assert response.data["orange_money_phone"] == "22370000002"

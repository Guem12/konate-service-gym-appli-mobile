import pytest

from accounts.models import User
from catalog.models import Product
from core.models import AuditLog
from orders.models import Order
from tests.conftest import login

pytestmark = pytest.mark.django_db


def test_dashboard_and_reports(auth_owner, catalog):
    dashboard = auth_owner.get("/api/v1/admin/dashboard")
    assert dashboard.status_code == 200
    for key in ("today", "sales_7_days", "sales_30_days", "categories", "alerts"):
        assert key in dashboard.data
    assert len(dashboard.data["sales_30_days"]) == 30

    reports = auth_owner.get("/api/v1/admin/reports")
    assert reports.status_code == 200
    assert "totals" in reports.data
    assert "top_products" in reports.data
    assert "stock" in reports.data


def test_csv_export(auth_owner, catalog):
    response = auth_owner.get("/api/v1/admin/reports/export?type=stock")
    assert response.status_code == 200
    assert "text/csv" in response["Content-Type"]
    assert "attachment" in response["Content-Disposition"]
    content = response.content.decode("utf-8-sig")
    assert "SKU" in content
    assert "KSG-TEST-20" in content


def test_create_product_with_nested_variants(auth_owner, catalog):
    payload = {
        "name": "Kettlebell pro",
        "category": catalog["category"].id,
        "description": "Fonte",
        "status": "published",
        "variants": [
            {"label": "16 kg", "sku": "KB-16", "price_purchase": 18000, "price_sale": 28000, "stock_qty": 5},
        ],
    }
    response = auth_owner.post("/api/v1/admin/products", payload, format="json")
    assert response.status_code == 201, response.data
    assert response.data["total_stock"] == 5
    product = Product.objects.get(pk=response.data["id"])
    assert product.variants.count() == 1


def test_price_change_is_audited(auth_owner, catalog):
    product = catalog["product"]
    variant = catalog["variant"]
    payload = {
        "name": product.name,
        "category": product.category_id,
        "brand": product.brand_id,
        "description": product.description,
        "status": "published",
        "variants": [
            {
                "id": variant.id, "label": variant.label, "sku": variant.sku,
                "price_purchase": variant.price_purchase, "price_sale": 52000,
                "stock_qty": variant.stock_qty, "low_stock_threshold": 3,
            }
        ],
    }
    response = auth_owner.put(f"/api/v1/admin/products/{product.id}", payload, format="json")
    assert response.status_code == 200, response.data
    assert AuditLog.objects.filter(action="product_price_change").exists()


def test_stock_adjustment(auth_owner, catalog):
    variant = catalog["variant"]
    response = auth_owner.post(
        "/api/v1/admin/stock-movements/adjust",
        {"variant": variant.id, "movement_type": "in", "quantity": 5, "reason": "Réception fournisseur"},
        format="json",
    )
    assert response.status_code == 201, response.data
    variant.refresh_from_db()
    assert variant.stock_qty == 15
    low = auth_owner.get("/api/v1/admin/stock-movements/low_stock")
    assert low.status_code == 200


def test_settings_update_owner_only(auth_owner, vendor, shop):
    response = auth_owner.patch(
        "/api/v1/admin/settings", {"whatsapp_phone": "22376543210"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["whatsapp_phone"] == "22376543210"

    login(auth_owner, vendor.phone, "Vendeur@2026")
    forbidden = auth_owner.patch(
        "/api/v1/admin/settings", {"whatsapp_phone": "22370000009"}, format="json"
    )
    assert forbidden.status_code == 403


def test_customer_block(auth_owner, client_user):
    response = auth_owner.post(
        f"/api/v1/admin/customers/{client_user.id}/block",
        {"is_blocked": True, "reason": "Impayés répétés"},
        format="json",
    )
    assert response.status_code == 200
    client_user.refresh_from_db()
    assert client_user.is_blocked is True
    blocked_login = login(auth_owner, client_user.phone, "Client@2026")
    assert blocked_login.status_code == 403

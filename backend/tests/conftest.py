import pytest
from rest_framework.test import APIClient

from accounts.models import Address, User
from catalog.models import Brand, Category, Product, ProductVariant
from core.models import ShopSetting


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def shop(db):
    shop = ShopSetting.load()
    shop.whatsapp_phone = "22370000001"
    shop.orange_money_phone = "22370000002"
    shop.save()
    return shop


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        phone="70000001", full_name="Mamadou Konaté", password="Owner@2026",
        role=User.Role.OWNER,
    )


@pytest.fixture
def vendor(db):
    return User.objects.create_user(
        phone="70000003", full_name="Fatoumata Traoré", password="Vendeur@2026",
        role=User.Role.VENDOR,
    )


@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        phone="70000002", full_name="Awa Diallo", password="Client@2026",
        role=User.Role.CLIENT,
    )


@pytest.fixture
def address(db, client_user):
    return Address.objects.create(
        user=client_user, label="Domicile", district="Hamdallaye",
        street="Rue 512", landmark="Pharmacie", phone=client_user.phone, is_default=True,
    )


@pytest.fixture
def catalog(db):
    category = Category.objects.create(name="Musculation", order=1)
    brand = Brand.objects.create(name="IronPro")
    product = Product.objects.create(
        name="Haltères hexagonaux", category=category, brand=brand,
        description="Haltères professionnels", is_featured=True,
        characteristics="Fonte\nCaoutchouc",
    )
    variant = ProductVariant.objects.create(
        product=product, label="20 kg", sku="KSG-TEST-20",
        price_purchase=32000, price_sale=48000, stock_qty=10, low_stock_threshold=3,
    )
    variant2 = ProductVariant.objects.create(
        product=product, label="10 kg", sku="KSG-TEST-10",
        price_purchase=18000, price_sale=28000, stock_qty=1, low_stock_threshold=3,
    )
    other = Product.objects.create(
        name="Tapis de course", category=category, brand=brand,
        description="Tapis pliable",
    )
    other_variant = ProductVariant.objects.create(
        product=other, label="T500", sku="KSG-TEST-T500",
        price_purchase=450000, price_sale=650000, stock_qty=3,
    )
    return {
        "category": category,
        "brand": brand,
        "product": product,
        "variant": variant,
        "variant2": variant2,
        "other": other,
        "other_variant": other_variant,
    }


def login(api, phone, password, otp_code=""):
    payload = {"phone": phone, "password": password}
    if otp_code:
        payload["otp_code"] = otp_code
    response = api.post("/api/v1/auth/login", payload, format="json")
    if response.status_code == 200:
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['tokens']['access']}")
    return response


@pytest.fixture
def auth_client(api, client_user, shop):
    response = login(api, client_user.phone, "Client@2026")
    assert response.status_code == 200
    return api


@pytest.fixture
def auth_owner(api, owner, shop):
    response = login(api, owner.phone, "Owner@2026")
    assert response.status_code == 200
    return api

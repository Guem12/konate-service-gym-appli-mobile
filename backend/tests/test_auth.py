import pyotp
import pytest

from accounts.models import User
from tests.conftest import login

pytestmark = pytest.mark.django_db


def test_register_and_login_with_normalized_phone(api, shop):
    response = api.post(
        "/api/v1/auth/register",
        {"full_name": "Awa Diallo", "phone": "+223 70 12 34 56", "password": "MotDePasse2026"},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["user"]["phone"] == "22370123456"
    assert response.data["tokens"]["access"]

    login_response = login(api, "70 12 34 56", "MotDePasse2026")
    assert login_response.status_code == 200
    me = api.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.data["full_name"] == "Awa Diallo"


def test_duplicate_phone_rejected(api, shop, client_user):
    response = api.post(
        "/api/v1/auth/register",
        {"full_name": "Doublon", "phone": client_user.phone, "password": "MotDePasse2026"},
        format="json",
    )
    assert response.status_code == 400
    assert "existe déjà" in str(response.data)


def test_login_lockout_after_repeated_failures(api, shop, client_user):
    for _ in range(5):
        response = login(api, client_user.phone, "MauvaisMotDePasse")
        assert response.status_code == 401
    locked = login(api, client_user.phone, "Client@2026")
    assert locked.status_code == 423
    assert locked.data["code"] == "locked"


def test_owner_direct_login(api, shop, owner):
    response = login(api, owner.phone, "Owner@2026")
    assert response.status_code == 200
    assert response.data["user"]["role"] == "owner"


def test_client_cannot_access_admin(api, shop, client_user):
    login(api, client_user.phone, "Client@2026")
    assert api.get("/api/v1/admin/dashboard").status_code == 403
    assert api.get("/api/v1/admin/customers").status_code == 403
    assert api.get("/api/v1/admin/settings").status_code == 403


def test_vendor_can_manage_catalog_but_not_users(api, shop, vendor):
    login(api, vendor.phone, "Vendeur@2026")
    assert api.get("/api/v1/admin/products").status_code == 200
    assert api.get("/api/v1/admin/orders").status_code == 200
    assert api.get("/api/v1/admin/users").status_code == 403
    assert api.get("/api/v1/admin/customers").status_code == 403
    assert api.get("/api/v1/admin/reports").status_code == 403


def test_account_deletion_anonymizes(api, shop, client_user, address):
    login(api, client_user.phone, "Client@2026")
    response = api.delete("/api/v1/auth/me/delete")
    assert response.status_code == 200
    client_user.refresh_from_db()
    assert client_user.is_active is False
    assert client_user.full_name == "Compte supprimé"
    assert not client_user.addresses.exists()

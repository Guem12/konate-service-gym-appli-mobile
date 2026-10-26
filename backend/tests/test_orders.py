import uuid

import pytest
from django.db.models import Sum

from catalog.models import Coupon
from inventory.models import StockMovement
from orders.models import Order
from payments.models import Payment
from tests.conftest import login

pytestmark = pytest.mark.django_db


def add_to_cart(api, variant, quantity=1):
    return api.post(
        "/api/v1/cart/items", {"variant": variant.id, "quantity": quantity}, format="json"
    )


def checkout(api, address, **overrides):
    payload = {
        "fulfillment": "delivery",
        "address": address.id,
        "payment_method": "cash",
        "delivery_slot": "Matin (08h-12h)",
    }
    payload.update(overrides)
    return api.post("/api/v1/orders", payload, format="json")


def test_cart_totals_and_stock_guard(api, catalog, client_user, shop):
    login(api, client_user.phone, "Client@2026")
    response = add_to_cart(api, catalog["variant"], 2)
    assert response.status_code == 201
    assert response.data["subtotal"] == 96000
    assert response.data["item_count"] == 2

    too_many = add_to_cart(api, catalog["variant2"], 5)
    assert too_many.status_code == 400
    assert "Stock insuffisant" in str(too_many.data)


def test_cash_checkout_decrements_stock(api, catalog, client_user, address, shop):
    login(api, client_user.phone, "Client@2026")
    add_to_cart(api, catalog["variant"], 2)
    response = checkout(api, address)
    assert response.status_code == 201, response.data
    order = Order.objects.get(pk=response.data["id"])
    assert order.total == 96000
    assert order.status == Order.Status.CONFIRMED
    assert order.number.startswith("KSG-")
    assert order.items.count() == 1

    catalog["variant"].refresh_from_db()
    assert catalog["variant"].stock_qty == 8
    movement = StockMovement.objects.get(order=order)
    assert movement.quantity == -2
    assert movement.movement_type == StockMovement.Type.SALE
    # Le panier est vidé après validation.
    assert api.get("/api/v1/cart").data["items"] == []


def test_insufficient_stock_rolls_back(api, catalog, client_user, address, shop):
    login(api, client_user.phone, "Client@2026")
    response = checkout(api, address, items=[{"variant": catalog["variant"].id, "quantity": 99}])
    assert response.status_code == 400
    assert Order.objects.count() == 0
    catalog["variant"].refresh_from_db()
    assert catalog["variant"].stock_qty == 10


def test_last_item_cannot_be_sold_twice(api, catalog, client_user, address, shop):
    login(api, client_user.phone, "Client@2026")
    first = checkout(api, address, items=[{"variant": catalog["variant2"].id, "quantity": 1}])
    assert first.status_code == 201
    second = checkout(api, address, items=[{"variant": catalog["variant2"].id, "quantity": 1}])
    assert second.status_code == 400
    catalog["variant2"].refresh_from_db()
    assert catalog["variant2"].stock_qty == 0
    assert Order.objects.count() == 1


def test_client_reference_is_idempotent(api, catalog, client_user, address, shop):
    login(api, client_user.phone, "Client@2026")
    reference = str(uuid.uuid4())
    payload = {
        "items": [{"variant": catalog["variant"].id, "quantity": 1}],
        "fulfillment": "delivery",
        "address": address.id,
        "payment_method": "cash",
        "client_reference": reference,
    }
    first = api.post("/api/v1/orders", payload, format="json")
    second = api.post("/api/v1/orders", payload, format="json")
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["number"] == second.data["number"]
    catalog["variant"].refresh_from_db()
    assert catalog["variant"].stock_qty == 9


def test_coupon_applied(api, catalog, client_user, address, shop):
    Coupon.objects.create(
        code="BIENVENUE10", discount_type=Coupon.DiscountType.PERCENTAGE,
        value=10, min_purchase=20000,
    )
    login(api, client_user.phone, "Client@2026")
    add_to_cart(api, catalog["variant"], 1)
    response = api.post("/api/v1/cart/coupon", {"code": "bienvenue10"}, format="json")
    assert response.status_code == 200
    assert response.data["discount"] == 4800
    order_response = checkout(api, address)
    assert order_response.status_code == 201
    order = Order.objects.get(pk=order_response.data["id"])
    assert order.discount == 4800
    assert order.total == 43200
    assert order.coupon_code == "BIENVENUE10"


def test_client_cancel_restocks(api, catalog, client_user, address, shop):
    login(api, client_user.phone, "Client@2026")
    add_to_cart(api, catalog["variant"], 3)
    order_id = checkout(api, address).data["id"]
    response = api.post(f"/api/v1/orders/{order_id}/cancel", {"reason": "Changement d'avis"}, format="json")
    assert response.status_code == 200, response.data
    order = Order.objects.get(pk=order_id)
    assert order.status == Order.Status.CANCELLED
    assert order.stock_restocked is True
    catalog["variant"].refresh_from_db()
    assert catalog["variant"].stock_qty == 10
    assert StockMovement.objects.filter(order=order, movement_type="return").count() == 1


def test_orange_money_requires_owner_confirmation(api, catalog, client_user, address, shop, owner):
    login(api, client_user.phone, "Client@2026")
    response = checkout(
        api, address, payment_method="orange_money", payment_reference="OM-2026-0001",
        items=[{"variant": catalog["variant"].id, "quantity": 1}],
    )
    assert response.status_code == 201, response.data
    order = Order.objects.get(pk=response.data["id"])
    assert order.status == Order.Status.PENDING_PAYMENT
    payment = Payment.objects.get(order=order)
    assert payment.status == Payment.Status.PENDING

    # Le propriétaire ne peut pas préparer avant vérification.
    login(api, owner.phone, "Owner@2026")
    blocked = api.post(f"/api/v1/admin/orders/{order.id}/status", {"status": "preparing"}, format="json")
    assert blocked.status_code == 400

    confirmed = api.post(f"/api/v1/admin/payments/{payment.id}/confirm")
    assert confirmed.status_code == 200, confirmed.data
    order.refresh_from_db()
    assert order.status == Order.Status.CONFIRMED
    assert order.amount_paid == order.total
    assert order.balance_due == 0
    assert order.payment_status == "paid"


def test_orange_money_reference_cannot_be_reused(api, catalog, client_user, address, shop, owner):
    payment_ref = "OM-UNIQUE-42"
    login(api, client_user.phone, "Client@2026")
    first = checkout(
        api, address, payment_method="orange_money", payment_reference=payment_ref,
        items=[{"variant": catalog["variant"].id, "quantity": 1}],
    )
    assert first.status_code == 201
    second = checkout(
        api, address, payment_method="orange_money", payment_reference=payment_ref,
        items=[{"variant": catalog["variant"].id, "quantity": 1}],
    )
    assert second.status_code == 400
    assert "déjà été utilisée" in str(second.data)
    catalog["variant"].refresh_from_db()
    assert catalog["variant"].stock_qty == 9


def test_delivery_completion_marks_order_delivered(api, catalog, client_user, address, shop, owner):
    login(api, client_user.phone, "Client@2026")
    order_id = checkout(
        api, address, items=[{"variant": catalog["variant"].id, "quantity": 1}]
    ).data["id"]
    login(api, owner.phone, "Owner@2026")
    delivery = api.get("/api/v1/admin/deliveries").data["results"][0]
    response = api.patch(
        f"/api/v1/admin/deliveries/{delivery['id']}",
        {"status": "delivered", "courier_name": "Moussa", "amount_collected": 48000},
        format="json",
    )
    assert response.status_code == 200, response.data
    order = Order.objects.get(pk=order_id)
    assert order.status == Order.Status.DELIVERED
    assert Payment.objects.filter(order=order, method="cash", status="pending").exists()


def test_invoice_pdf(api, catalog, client_user, address, shop):
    login(api, client_user.phone, "Client@2026")
    order_id = checkout(
        api, address, items=[{"variant": catalog["variant"].id, "quantity": 1}]
    ).data["id"]
    response = api.get(f"/api/v1/orders/{order_id}/invoice?kind=invoice")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    content = b"".join(response.streaming_content)
    assert content.startswith(b"%PDF")


def test_sale_receipt_requires_a_payment(api, catalog, client_user, address, shop):
    login(api, client_user.phone, "Client@2026")
    order_id = checkout(
        api, address, items=[{"variant": catalog["variant"].id, "quantity": 1}]
    ).data["id"]
    response = api.get(f"/api/v1/orders/{order_id}/invoice?kind=receipt")
    assert response.status_code == 400
    assert "Aucun encaissement" in str(response.data)


def test_sale_receipt_after_payment_is_shareable(
    api, catalog, client_user, address, shop, owner
):
    login(api, client_user.phone, "Client@2026")
    order_id = checkout(
        api,
        address,
        payment_method="orange_money",
        payment_reference="OM-RECU-001",
        items=[{"variant": catalog["variant"].id, "quantity": 1}],
    ).data["id"]
    payment = Payment.objects.get(order_id=order_id)

    login(api, owner.phone, "Owner@2026")
    confirmed = api.post(f"/api/v1/admin/payments/{payment.id}/confirm")
    assert confirmed.status_code == 200, confirmed.data

    login(api, client_user.phone, "Client@2026")
    response = api.get(f"/api/v1/orders/{order_id}/invoice?kind=receipt")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "recu" in response["Content-Disposition"]
    content = b"".join(response.streaming_content)
    assert content.startswith(b"%PDF")
    # Le reçu doit rester lisible et non vide.
    assert len(content) > 1500


def test_other_client_cannot_read_order(api, catalog, client_user, address, shop):
    from accounts.models import User

    other = User.objects.create_user(
        phone="70000009", full_name="Autre", password="Autre@2026", role=User.Role.CLIENT
    )
    login(api, client_user.phone, "Client@2026")
    order_id = checkout(
        api, address, items=[{"variant": catalog["variant"].id, "quantity": 1}]
    ).data["id"]
    api.credentials()
    login(api, other.phone, "Autre@2026")
    response = api.get(f"/api/v1/orders/{order_id}")
    assert response.status_code == 404

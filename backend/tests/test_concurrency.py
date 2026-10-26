import threading

import pytest
from django.db import close_old_connections, connection
from rest_framework.exceptions import ValidationError

from accounts.models import User
from catalog.models import Category, Product, ProductVariant
from orders.services import create_order

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.skipif(connection.vendor != "postgresql", reason="verrouillage testé sous PostgreSQL")
def test_two_concurrent_orders_cannot_sell_last_item():
    category = Category.objects.create(name="Cardio")
    product = Product.objects.create(name="Rameur", category=category)
    variant = ProductVariant.objects.create(
        product=product, label="Unique", sku="RAM-001",
        price_purchase=300000, price_sale=450000, stock_qty=1,
    )
    user_a = User.objects.create_user(phone="70000021", full_name="A", password="Test@2026")
    user_b = User.objects.create_user(phone="70000022", full_name="B", password="Test@2026")

    results = []
    barrier = threading.Barrier(2)

    def attempt(user):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            create_order(
                user=user,
                items=[{"variant": variant.id, "quantity": 1}],
                fulfillment="pickup",
                payment_method="cash",
            )
            results.append("ok")
        except ValidationError:
            results.append("refused")
        except Exception as exc:  # pragma: no cover - diagnostic
            results.append(f"error:{exc}")
        finally:
            close_old_connections()

    threads = [threading.Thread(target=attempt, args=(user,)) for user in (user_a, user_b)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    variant.refresh_from_db()
    assert results.count("ok") == 1, results
    assert results.count("refused") == 1, results
    assert variant.stock_qty == 0

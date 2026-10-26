"""Vérification de bout en bout des parcours utilisés par l'application Flutter.

À lancer avec le serveur Django actif :
    ../.venv/Scripts/python.exe scripts/smoke_app.py [http://127.0.0.1:8000/api/v1]
"""
import json
import sys
import uuid

import pyotp
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api/v1"
checks = []


def check(label, condition, detail=""):
    checks.append((label, bool(condition), detail))
    status = "OK " if condition else "ÉCHEC"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not condition else ""))


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def login(phone, password, otp=""):
    payload = {"phone": phone, "password": password}
    if otp:
        payload["otp_code"] = otp
    return requests.post(f"{BASE}/auth/login", json=payload, timeout=15)


def main():
    health = requests.get(f"{BASE}/health", timeout=15)
    check("santé de l'API", health.status_code == 200, health.text[:120])

    # --- Client -----------------------------------------------------------
    response = login("70000002", "Client@2026")
    check("connexion client", response.status_code == 200, response.text[:160])
    client_tokens = response.json()["tokens"]
    client = client_tokens["access"]

    me = requests.get(f"{BASE}/auth/me", headers=auth(client), timeout=15)
    check("profil client", me.status_code == 200 and me.json()["role"] == "client")

    home = requests.get(f"{BASE}/home", headers=auth(client), timeout=15)
    home_data = home.json()
    check(
        "accueil (bannières, catégories, produits)",
        home.status_code == 200
        and "categories" in home_data
        and "popular" in home_data,
        home.text[:160],
    )

    products = requests.get(f"{BASE}/products", params={"search": "halt"}, timeout=15)
    results = products.json().get("results", [])
    check("recherche produit", products.status_code == 200 and len(results) > 0)
    product = results[0] if results else None

    detail = requests.get(f"{BASE}/products/{product['id']}", timeout=15).json()
    check(
        "fiche produit (variantes)",
        bool(detail.get("variants")),
        json.dumps(detail)[:160],
    )
    variant = next(v for v in detail["variants"] if v["stock_qty"] > 0)

    wa = requests.get(
        f"{BASE}/whatsapp/link", params={"product": product["id"]}, timeout=15
    )
    check("lien WhatsApp produit", wa.status_code == 200 and "wa.me" in wa.text)

    settings = requests.get(f"{BASE}/settings", timeout=15)
    check(
        "réglages boutique",
        settings.status_code == 200 and settings.json()["shop_name"],
    )

    addresses = requests.get(f"{BASE}/me/addresses", headers=auth(client), timeout=15).json()
    address_list = addresses.get("results", addresses) if isinstance(addresses, dict) else addresses
    if address_list:
        address_id = address_list[0]["id"]
    else:
        created = requests.post(
            f"{BASE}/me/addresses",
            headers=auth(client),
            json={"label": "Smoke", "district": "Badalabougou", "is_default": True},
            timeout=15,
        )
        address_id = created.json()["id"]
    check("adresses de livraison", address_id is not None)

    cart = requests.post(
        f"{BASE}/cart/items",
        headers=auth(client),
        json={"variant": variant["id"], "quantity": 1},
        timeout=15,
    )
    check("ajout au panier", cart.status_code in (200, 201), cart.text[:160])

    order = requests.post(
        f"{BASE}/orders",
        headers=auth(client),
        json={
            "fulfillment": "delivery",
            "address": address_id,
            "payment_method": "cash",
            "client_reference": str(uuid.uuid4()),
        },
        timeout=20,
    )
    order_data = order.json()
    check("validation de commande", order.status_code in (200, 201), order.text[:200])
    order_id = order_data["id"]

    my_orders = requests.get(f"{BASE}/orders", headers=auth(client), timeout=15)
    check(
        "liste des commandes",
        my_orders.status_code == 200 and my_orders.json()["count"] >= 1,
    )

    detail_order = requests.get(f"{BASE}/orders/{order_id}", headers=auth(client), timeout=15)
    check(
        "détail commande + suivi",
        detail_order.status_code == 200 and "timeline" in detail_order.json(),
    )

    invoice = requests.get(
        f"{BASE}/orders/{order_id}/invoice", params={"kind": "invoice"}, headers=auth(client), timeout=20
    )
    check(
        "facture PDF",
        invoice.status_code == 200 and invoice.content.startswith(b"%PDF"),
    )

    # --- Administration ---------------------------------------------------
    owner_login = login("70000001", "Owner@2026")
    check(
        "2FA exigée pour le propriétaire",
        owner_login.status_code == 401 and "otp" in owner_login.text,
        owner_login.text[:120],
    )
    otp = pyotp.TOTP("JBSWY3DPEHPK3PXP").now()
    owner_login = login("70000001", "Owner@2026", otp)
    check("connexion propriétaire avec 2FA", owner_login.status_code == 200, owner_login.text[:160])
    owner = owner_login.json()["tokens"]["access"]

    dashboard = requests.get(f"{BASE}/admin/dashboard", headers=auth(owner), timeout=15)
    check("tableau de bord", dashboard.status_code == 200, dashboard.text[:160])

    admin_orders = requests.get(f"{BASE}/admin/orders", headers=auth(owner), timeout=15)
    check("commandes administrateur", admin_orders.status_code == 200)

    advance = requests.post(
        f"{BASE}/admin/orders/{order_id}/status",
        headers=auth(owner),
        json={"status": "preparing"},
        timeout=15,
    )
    check("changement de statut", advance.status_code == 200, advance.text[:160])

    deliveries = requests.get(f"{BASE}/admin/deliveries", headers=auth(owner), timeout=15)
    check("liste des livraisons", deliveries.status_code == 200)

    admin_products = requests.get(f"{BASE}/admin/products", headers=auth(owner), timeout=15)
    check("catalogue administrateur", admin_products.status_code == 200)

    # --- Reçu de vente : après encaissement seulement ---------------------
    requests.post(
        f"{BASE}/cart/items",
        headers=auth(client),
        json={"variant": variant["id"], "quantity": 1},
        timeout=15,
    )
    om_order = requests.post(
        f"{BASE}/orders",
        headers=auth(client),
        json={
            "fulfillment": "delivery",
            "address": address_id,
            "payment_method": "orange_money",
            "payment_reference": f"OM-SMOKE-{uuid.uuid4().hex[:8].upper()}",
            "client_reference": str(uuid.uuid4()),
        },
        timeout=20,
    )
    check("commande Orange Money", om_order.status_code in (200, 201), om_order.text[:160])
    om_order_id = om_order.json()["id"]

    early = requests.get(
        f"{BASE}/orders/{om_order_id}/invoice",
        params={"kind": "receipt"},
        headers=auth(client),
        timeout=15,
    )
    check("reçu refusé avant encaissement", early.status_code == 400, early.text[:120])

    pending = requests.get(
        f"{BASE}/admin/payments/pending", headers=auth(owner), timeout=15
    ).json()
    payment = next(
        (p for p in pending.get("results", []) if p["order"] == om_order_id), None
    )
    check("paiement en attente listé", payment is not None)

    if payment:
        confirmed = requests.post(
            f"{BASE}/admin/payments/{payment['id']}/confirm", headers=auth(owner), timeout=15
        )
        check("confirmation de l'encaissement", confirmed.status_code == 200, confirmed.text[:160])

    receipt = requests.get(
        f"{BASE}/orders/{om_order_id}/invoice",
        params={"kind": "receipt"},
        headers=auth(owner),
        timeout=20,
    )
    check(
        "reçu de vente PDF après encaissement",
        receipt.status_code == 200
        and receipt.content.startswith(b"%PDF")
        and "recu" in receipt.headers.get("Content-Disposition", ""),
        receipt.text[:120] if receipt.status_code != 200 else "",
    )

    # --- Sécurité ---------------------------------------------------------
    forbidden = requests.get(f"{BASE}/admin/dashboard", headers=auth(client), timeout=15)
    check("client interdit sur l'admin", forbidden.status_code in (401, 403))

    anonymous = requests.get(f"{BASE}/orders", timeout=15)
    check("commandes protégées", anonymous.status_code == 401)

    failed = [label for label, ok, _ in checks if not ok]
    print("\n%d vérifications, %d échec(s)" % (len(checks), len(failed)))
    if failed:
        print("Échecs : " + ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()

# Konaté-Service-Gym

Application de vente d'équipements de sport à Bamako : API Django/DRF + application
mobile Flutter (client et gestion) pour une boutique familiale qui vend aujourd'hui
par WhatsApp.

Le projet couvre le parcours complet : catalogue, panier, commande avec livraison ou
retrait, paiement espèces ou Orange Money, suivi de commande, reçu de vente PDF
partageable, gestion du stock, des encaissements, des livraisons et des clients côté
boutique.

```
backend/   API Django 5 + DRF + PostgreSQL (JWT, 2FA, stock transactionnel, PDF)
app/       Application Flutter (Android/iOS)
```

## 1. Démarrage du backend

Prérequis : Python 3.11+, PostgreSQL 14+.

```bash
# à la racine du dépôt
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt   # Windows
# source .venv/bin/activate && pip install -r backend/requirements.txt  # macOS/Linux

cp backend/.env.example backend/.env    # puis renseigner DATABASE_URL et DJANGO_SECRET_KEY
cd backend
../.venv/Scripts/python.exe manage.py migrate
../.venv/Scripts/python.exe manage.py seed_demo     # jeu de données de démonstration
../.venv/Scripts/python.exe manage.py runserver
```

L'API répond sur `http://127.0.0.1:8000/api/v1/`, la documentation OpenAPI sur
`/api/docs` et `/api/schema`.

### Comptes de démonstration

| Rôle | Téléphone | Mot de passe | Remarque |
| --- | --- | --- | --- |
| Propriétaire | 70 00 00 01 | `Owner@2026` | double authentification active |
| Vendeur | 70 00 00 03 | `Vendeur@2026` | catalogue, commandes, stock |
| Client | 70 00 00 02 | `Client@2026` | panier et commandes |
| Client 2 | 70 00 00 04 | `Client@2026` | second compte pour tester l'isolation |

Le secret TOTP du propriétaire est affiché par `seed_demo` (et stocké dans
`accounts.User.totp_secret`). En développement, le code courant se calcule avec
`pyotp.TOTP(secret).now()`.

## 2. Démarrage de l'application Flutter

```bash
cd app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

# Aperçu navigateur (pratique pour montrer le parcours sans téléphone)
flutter run -d web-server --web-port=8080 \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1

# APK de test
flutter build apk --debug     # app/build/app/outputs/flutter-apk/app-debug.apk
```

- `10.0.2.2` est l'adresse de la machine hôte vue depuis l'émulateur Android.
- Sur un téléphone réel, utiliser l'IP du poste : `--dart-define=API_BASE_URL=http://192.168.1.20:8000/api/v1`.
- En production, pointer vers l'URL HTTPS de l'API.

## 3. Vérifications

```bash
# API : 36 tests (auth, 2FA, catalogue, panier, stock, concurrence, PDF, reçu, admin)
cd backend && ../.venv/Scripts/python.exe -m pytest -q

# Parcours complets sur un serveur actif (28 vérifications)
cd backend && ../.venv/Scripts/python.exe scripts/smoke_app.py

# Application
cd app && flutter analyze && flutter test
```

Le test de concurrence (`tests/test_concurrency.py`) vérifie qu'un même dernier
exemplaire ne peut pas être vendu deux fois : il s'exécute sur PostgreSQL, pas sur
SQLite.

## 4. Choix techniques

**Argent.** Tous les montants sont des entiers en francs CFA, côté API comme côté
application. Aucun flottant ne touche à l'argent.

**Stock.** Chaque sortie passe par `inventory.record_movement`, qui verrouille la
ligne de variante (`select_for_update`) avant de décrémenter. Une commande
annulée remet les articles en stock une seule fois (`stock_restocked`).

**Idempotence des commandes.** L'application envoie un `client_reference` (UUID).
Si le réseau coupe après l'envoi, un nouvel essai renvoie la commande existante au
lieu d'en créer une seconde.

**Sécurité.** JWT courts + rafraîchissement, verrouillage du compte après plusieurs
échecs de connexion, 2FA TOTP obligatoire pour les comptes d'administration,
journal d'audit sur les actions sensibles (prix, stock, statuts), téléphone
normalisé au format `223XXXXXXXX`.

**Paiement Orange Money.** Le client déclare une référence de transfert ; la
commande reste `pending_payment` jusqu'à confirmation explicite par la boutique.
Une référence ne peut pas servir deux fois.

**Reçu de vente.** Un reçu PDF n'est émis que pour une commande réellement encaissée
(`amount_paid > 0`) : l'API refuse sinon. La boutique le génère depuis l'onglet
« Encaissements » après avoir confirmé le paiement, puis le partage au client via la
feuille de partage du téléphone (WhatsApp, e-mail, enregistrement). Le client peut le
retrouver depuis sa commande dès qu'un paiement est confirmé. Le reçu reprend les
encaissements (date, moyen, référence Orange Money, montant), le total, le reste à
payer et le délai d'échange.

**Application.** Un seul code pour les deux rôles : l'onglet « Gestion » n'apparaît
que pour le personnel. Le panier vit côté serveur, donc il suit le client d'un
appareil à l'autre. L'état passe par `provider`, les appels par un client HTTP
unique qui rafraîchit le jeton et remonte des messages d'erreur déjà lisibles.

## 5. Structure

```
backend/
  config/        réglages, URLs, WSGI/ASGI
  core/          réglages boutique, notifications, WhatsApp, PDF, audit, permissions
  accounts/      utilisateurs, adresses, JWT, 2FA, clients (admin)
  catalog/       produits, variantes, catégories, promotions, favoris, codes promo
  inventory/     mouvements de stock, fournisseurs
  orders/        panier, commandes, transitions de statut
  payments/      encaissements, confirmation Orange Money
  deliveries/    livraisons, encaissement à la remise
  reports/       tableau de bord, rapports, export CSV
  tests/         suite pytest
  scripts/       smoke_app.py
app/lib/
  api/           client HTTP + dépôt de données
  core/          thème, formatage, composants
  models/        modèles JSON
  state/         authentification, panier
  screens/       écrans client + admin/
```

## 6. Limites connues

- Les notifications push sont préparées côté API (`core/push.py`, jetons
  d'appareil) mais aucun service FCM n'est branché : il faut les identifiants du
  projet Firebase.
- Le reçu PDF se partage depuis Android/iOS ; sur le web, l'application affiche un
  message explicite car le système n'expose pas la feuille de partage de fichiers.
- Les photos produits sont stockées dans `media/` en développement ; prévoir un
  stockage objet (S3/R2) en production.
# konate-service-gym-appli-mobile

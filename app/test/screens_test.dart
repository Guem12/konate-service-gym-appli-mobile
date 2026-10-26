import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:konate_gym/api/repository.dart';
import 'package:konate_gym/core/theme.dart';
import 'package:konate_gym/models/models.dart';
import 'package:konate_gym/screens/home_screen.dart';
import 'package:konate_gym/screens/login_screen.dart';
import 'package:konate_gym/screens/order_detail_screen.dart';
import 'package:konate_gym/services/receipt_service.dart';
import 'package:konate_gym/state/auth_state.dart';
import 'package:provider/provider.dart';

import 'package:konate_gym/api/api_client.dart';

/// Dépôt factice : aucun appel réseau, données réalistes.
class _FakeRepository extends Repository {
  _FakeRepository() : super(ApiClient());

  @override
  Future<HomeData> home() async => HomeData(
        categories: [
          Category(id: 1, name: 'Musculation', productCount: 12),
          Category(id: 2, name: 'Cardio', productCount: 5),
        ],
        popular: [
          Product(
            id: 1,
            name: 'Haltères hexagonaux 10 kg',
            slug: 'halteres-10',
            price: 48000,
            comparePrice: 55000,
            stockStatus: 'in_stock',
            categoryName: 'Musculation',
          ),
        ],
        newArrivals: [
          Product(
            id: 2,
            name: 'Tapis de yoga premium',
            slug: 'tapis-yoga',
            price: 15000,
            stockStatus: 'in_stock',
          ),
        ],
      );

  @override
  Future<ShopSettings> settings() async => ShopSettings(
        shopName: 'Konaté-Service-Gym',
        address: 'Hamdallaye ACI 2000, Bamako',
        openingHours: 'Lun-Sam 09h-19h',
      );
}

/// Session factice : la connexion réussit sans réseau.
class _FakeAuth extends AuthState {
  _FakeAuth() : super(ApiClient());

  @override
  Future<void> login({
    required String phone,
    required String password,
    String otpCode = '',
  }) async {
    user = User(id: 1, phone: phone, fullName: 'Awa Diallo');
    notifyListeners();
  }
}

/// Dépôt ne servant qu'une commande, pour tester l'écran de détail.
class _OrderRepository extends Repository {
  _OrderRepository(this.detail) : super(ApiClient());

  final OrderDetail detail;

  @override
  Future<OrderDetail> order(int id) async => detail;
}

/// Service de reçu factice : mémorise l'appel au partage.
class _FakeReceipt extends ReceiptService {
  _FakeReceipt() : super(ApiClient());

  int? sharedOrderId;

  @override
  Future<String> share({
    required int orderId,
    String orderLabel = '',
    String customerName = '',
  }) async {
    sharedOrderId = orderId;
    return '/tmp/recu.pdf';
  }
}

OrderDetail _order({int amountPaid = 0, bool canCancel = false}) => OrderDetail(
      id: 42,
      number: 'KSG-2610-00042',
      status: amountPaid > 0 ? 'delivered' : 'confirmed',
      statusLabel: amountPaid > 0 ? 'Livrée' : 'Confirmée',
      total: 48000,
      amountPaid: amountPaid,
      balanceDue: 48000 - amountPaid,
      canCancel: canCancel,
      customerName: 'Awa Diallo',
      lines: [
        OrderLine(productName: 'Haltères hexagonaux', quantity: 1, unitPrice: 48000),
      ],
    );

void main() {
  testWidgets('l\'accueil affiche les sections du catalogue', (tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider<AuthState>(
        create: (_) => _FakeAuth(),
        child: Provider<Repository>.value(
          value: _FakeRepository(),
          child: MaterialApp(theme: buildTheme(), home: const HomeScreen()),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Konaté-Service-Gym'), findsOneWidget);
    expect(find.text('Catégories'), findsOneWidget);
    expect(find.text('Musculation'), findsOneWidget);
    expect(find.text('Les plus vendus'), findsOneWidget);
    expect(find.text('Haltères hexagonaux 10 kg'), findsOneWidget);

    // Les sections basses se construisent au défilement (ListView paresseuse).
    final page = find.byWidgetPredicate(
      (widget) => widget is Scrollable && widget.axisDirection == AxisDirection.down,
    ).first;
    await tester.scrollUntilVisible(find.textContaining('Nouveautés'), 260, scrollable: page);
    expect(find.text('Tapis de yoga premium'), findsOneWidget);

    await tester.scrollUntilVisible(find.text('La boutique'), 260, scrollable: page);
    expect(find.text('Hamdallaye ACI 2000, Bamako'), findsOneWidget);
  });

  testWidgets('une commande encaissée propose le partage du reçu', (tester) async {
    final receipt = _FakeReceipt();
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          Provider<Repository>.value(value: _OrderRepository(_order(amountPaid: 48000))),
          Provider<ReceiptService>.value(value: receipt),
        ],
        child: MaterialApp(
          theme: buildTheme(),
          home: const OrderDetailScreen(orderId: 42),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Partager le reçu'), findsOneWidget);
    await tester.tap(find.text('Partager le reçu'));
    await tester.pumpAndSettle();
    expect(receipt.sharedOrderId, 42);
  });

  testWidgets('une commande non payée n\'affiche pas de reçu', (tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          Provider<Repository>.value(value: _OrderRepository(_order(canCancel: true))),
          Provider<ReceiptService>.value(value: _FakeReceipt()),
        ],
        child: MaterialApp(
          theme: buildTheme(),
          home: const OrderDetailScreen(orderId: 42),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Partager le reçu'), findsNothing);
    expect(find.text('Annuler'), findsOneWidget);
  });

  testWidgets('la connexion valide le numéro avant l\'appel réseau', (tester) async {
    final auth = _FakeAuth();
    await tester.pumpWidget(
      ChangeNotifierProvider<AuthState>.value(
        value: auth,
        child: MaterialApp(theme: buildTheme(), home: const LoginScreen()),
      ),
    );

    await tester.tap(find.text('Se connecter'));
    await tester.pump();

    expect(find.text('Entrez 8 chiffres (ex. 70 00 00 00).'), findsOneWidget);
    expect(find.text('Saisissez votre mot de passe.'), findsOneWidget);
    expect(auth.user, isNull);

    await tester.enterText(find.byType(TextFormField).at(0), '70 00 00 02');
    await tester.enterText(find.byType(TextFormField).at(1), 'Client@2026');
    await tester.tap(find.text('Se connecter'));
    await tester.pumpAndSettle();

    expect(auth.user?.phone, '22370000002');
    expect(find.text('Entrez 8 chiffres (ex. 70 00 00 00).'), findsNothing);
  });
}

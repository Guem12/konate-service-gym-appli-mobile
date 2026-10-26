import 'package:flutter_test/flutter_test.dart';
import 'package:konate_gym/core/format.dart';
import 'package:konate_gym/models/models.dart';

void main() {
  group('Formatage', () {
    test('les montants sont séparés et suffixés', () {
      // Le format français utilise une espace insécable étroite comme séparateur.
      String flat(String value) => value.replaceAll(RegExp(r'\s'), ' ');
      expect(flat(money(48000)), '48 000 FCFA');
      expect(flat(money(0)), '0 FCFA');
    });

    test('un numéro malien est normalisé puis affiché', () {
      expect(normalizePhoneInput('+223 70 12 34 56'), '22370123456');
      expect(normalizePhoneInput('70 12 34 56'), '22370123456');
      expect(prettyPhone('22370123456'), '+223 70 12 34 56');
    });
  });

  group('Modèles', () {
    test('un produit en promotion expose les deux prix', () {
      final product = Product.fromJson({
        'id': 1,
        'name': 'Haltères',
        'slug': 'halteres',
        'price': 48000,
        'compare_price': 60000,
        'stock_status': 'in_stock',
        'category_name': 'Musculation',
      });
      expect(product.hasPromotion, isTrue);
      expect(product.inStock, isTrue);
    });

    test('le panier calcule le total de ligne', () {
      final item = CartItem.fromJson({
        'id': 3,
        'variant': 7,
        'product_name': 'Tapis',
        'quantity': 2,
        'unit_price': 15000,
        'stock_qty': 4,
      });
      expect(item.lineTotal, 30000);
    });

    test('une commande livrée n\'est plus annulable côté client', () {
      final order = OrderSummary.fromJson({
        'id': 9,
        'number': 'KSG-2610-00009',
        'status': 'delivered',
        'status_display': 'Livrée',
        'total': 20000,
        'can_cancel': false,
      });
      expect(order.isOpen, isFalse);
    });

    test('le rôle détermine l\'accès à la gestion', () {
      final vendor = User.fromJson({'id': 2, 'phone': '70000002', 'role': 'vendor'});
      final client = User.fromJson({'id': 3, 'phone': '70000003', 'role': 'client'});
      expect(vendor.isStaff, isTrue);
      expect(client.isStaff, isFalse);
    });
  });
}

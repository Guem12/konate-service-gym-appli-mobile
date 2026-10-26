import 'package:flutter/foundation.dart';

import '../api/api_client.dart';
import '../models/models.dart';

/// Panier serveur : il survit à la fermeture de l'application et reste
/// synchronisé avec les prix et le stock réels.
class CartState extends ChangeNotifier {
  CartState(this.api);

  final ApiClient api;

  Cart cart = Cart();
  bool loading = false;
  String? error;

  int get itemCount => cart.itemCount;

  Future<void> load({bool silent = false}) async {
    if (!silent) {
      loading = true;
      notifyListeners();
    }
    try {
      final data = await api.get('/cart');
      if (data is Map<String, dynamic>) {
        cart = Cart.fromJson(data);
        error = null;
      }
    } on ApiException catch (e) {
      error = e.message;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// Ajoute un article ; renvoie un message d'erreur lisible ou `null`.
  Future<String?> add(int variantId, {int quantity = 1}) async {
    try {
      final data = await api.post('/cart/items', body: {
        'variant': variantId,
        'quantity': quantity,
      });
      if (data is Map<String, dynamic>) {
        cart = Cart.fromJson(data);
        notifyListeners();
      }
      return null;
    } on ApiException catch (e) {
      return e.message;
    }
  }

  Future<String?> updateQuantity(int itemId, int quantity) async {
    try {
      if (quantity <= 0) {
        await api.delete('/cart/items/$itemId');
      } else {
        await api.patch('/cart/items/$itemId', body: {'quantity': quantity});
      }
      await load(silent: true);
      return null;
    } on ApiException catch (e) {
      return e.message;
    }
  }

  Future<String?> remove(int itemId) => updateQuantity(itemId, 0);

  Future<String?> applyCoupon(String code) async {
    try {
      await api.post('/cart/coupon', body: {'code': code.trim()});
      await load(silent: true);
      return null;
    } on ApiException catch (e) {
      return e.message;
    }
  }

  void reset() {
    cart = Cart();
    notifyListeners();
  }
}

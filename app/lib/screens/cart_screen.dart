import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/format.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import '../state/cart_state.dart';
import 'checkout_screen.dart';
import 'catalog_screen.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  final _coupon = TextEditingController();
  bool _applyingCoupon = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<CartState>().load();
    });
  }

  @override
  void dispose() {
    _coupon.dispose();
    super.dispose();
  }

  Future<void> _applyCoupon() async {
    final code = _coupon.text.trim();
    if (code.isEmpty) return;
    setState(() => _applyingCoupon = true);
    final error = await context.read<CartState>().applyCoupon(code);
    if (!mounted) return;
    setState(() => _applyingCoupon = false);
    if (error != null) {
      showMessage(context, error);
    } else {
      _coupon.clear();
      showMessage(context, 'Code promo appliqué.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final cartState = context.watch<CartState>();
    final cart = cartState.cart;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mon panier'),
        actions: [
          if (!cart.isEmpty)
            TextButton(
              onPressed: () async {
                for (final item in List<CartItem>.from(cart.items)) {
                  await cartState.remove(item.id);
                }
              },
              child: const Text('Vider'),
            ),
        ],
      ),
      body: cartState.loading && cart.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : cart.isEmpty
              ? EmptyState(
                  icon: Icons.shopping_bag_rounded,
                  title: 'Votre panier est vide',
                  message: 'Parcourez le catalogue et ajoutez vos équipements.',
                  action: FilledButton(
                    style: FilledButton.styleFrom(minimumSize: const Size(200, 48)),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const CatalogScreen()),
                    ),
                    child: const Text('Voir le catalogue'),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                  children: [
                    for (final item in cart.items) _cartTile(item),
                    const SizedBox(height: 16),
                    _couponCard(cart),
                    const SizedBox(height: 16),
                    _totalsCard(cart),
                  ],
                ),
      bottomNavigationBar: cart.isEmpty ? null : _checkoutBar(cart),
    );
  }

  Widget _cartTile(CartItem item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ProductThumb(url: item.imageUrl, size: 72),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.productName,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                if (item.variantLabel.isNotEmpty)
                  Text(
                    item.variantLabel,
                    style: const TextStyle(fontSize: 12, color: KsgColors.muted),
                  ),
                const SizedBox(height: 6),
                Text(
                  money(item.lineTotal),
                  style: const TextStyle(fontWeight: FontWeight.w800, color: KsgColors.greenDark),
                ),
                Row(
                  children: [
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      onPressed: () => context.read<CartState>().updateQuantity(item.id, item.quantity - 1),
                      icon: const Icon(Icons.remove_circle_rounded, size: 20, color: KsgColors.red),
                    ),
                    Text('${item.quantity}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      onPressed: item.quantity >= item.stockQty
                          ? null
                          : () => context.read<CartState>().updateQuantity(item.id, item.quantity + 1),
                      icon: const Icon(Icons.add_circle_rounded, size: 20, color: KsgColors.green),
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: () => _confirmRemove(item),
                      child: const Text('Retirer', style: TextStyle(color: KsgColors.red)),
                    ),
                  ],
                ),
                if (item.quantity >= item.stockQty)
                  Text(
                    'Stock maximum atteint (${item.stockQty})',
                    style: const TextStyle(fontSize: 11, color: KsgColors.muted),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmRemove(CartItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Retirer cet article ?'),
        content: Text(item.productName),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Retirer')),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await context.read<CartState>().remove(item.id);
    }
  }

  Widget _couponCard(Cart cart) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Code promo', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _coupon,
                  textCapitalization: TextCapitalization.characters,
                  decoration: const InputDecoration(hintText: 'BIENVENUE10'),
                ),
              ),
              const SizedBox(width: 10),
              FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size(110, 48)),
                onPressed: _applyingCoupon ? null : _applyCoupon,
                child: const Text('Appliquer'),
              ),
            ],
          ),
          if (cart.couponCode.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Code actif : ${cart.couponCode}',
                style: const TextStyle(color: KsgColors.green, fontWeight: FontWeight.w600),
              ),
            ),
        ],
      ),
    );
  }

  Widget _totalsCard(Cart cart) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        children: [
          _row('Sous-total', money(cart.subtotal)),
          if (cart.discount > 0) _row('Remise', '- ${money(cart.discount)}'),
          const Divider(height: 20),
          _row('Total', money(cart.total), bold: true),
          const SizedBox(height: 6),
          const Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Frais de livraison précisés à l\'étape suivante selon la zone.',
              style: TextStyle(fontSize: 11.5, color: KsgColors.muted),
            ),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontWeight: bold ? FontWeight.w800 : FontWeight.w500)),
          Text(
            value,
            style: TextStyle(
              fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
              fontSize: bold ? 17 : 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _checkoutBar(Cart cart) {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(top: BorderSide(color: Color(0xFFEFEBE0))),
        ),
        child: Row(
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Total', style: TextStyle(fontSize: 11, color: KsgColors.muted)),
                Text(
                  money(cart.total),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                ),
              ],
            ),
            const SizedBox(width: 16),
            Expanded(
              child: FilledButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const CheckoutScreen()),
                ),
                child: Text('Commander (${cart.itemCount})'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../api/repository.dart';
import '../../core/format.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';

class AdminProductsScreen extends StatefulWidget {
  const AdminProductsScreen({super.key});

  @override
  State<AdminProductsScreen> createState() => _AdminProductsScreenState();
}

class _AdminProductsScreenState extends State<AdminProductsScreen> {
  final _search = TextEditingController();
  late Future<List<Product>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<List<Product>> _load() => context.read<Repository>().adminProducts(search: _search.text);

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _adjustStock(Product product) async {
    final variant = await showModalBottomSheet<ProductVariant>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Text('Choisir la variante', style: TextStyle(fontWeight: FontWeight.w800)),
            ),
            for (final variant in product.variants)
              ListTile(
                title: Text(variant.label),
                subtitle: Text('${variant.stockQty} en stock · ${money(variant.price)}'),
                onTap: () => Navigator.pop(context, variant),
              ),
          ],
        ),
      ),
    );
    if (variant == null || !mounted) return;

    final quantity = TextEditingController();
    final reason = TextEditingController();
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Mouvement de stock — ${variant.label}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: quantity,
              keyboardType: const TextInputType.numberWithOptions(signed: true),
              decoration: const InputDecoration(
                labelText: 'Quantité',
                hintText: 'Ex. 5 ou -2',
                helperText: 'Positif = entrée, négatif = sortie',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: reason,
              decoration: const InputDecoration(labelText: 'Motif'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Valider')),
        ],
      ),
    );
    final value = int.tryParse(quantity.text.trim());
    if (saved != true || value == null || value == 0 || !mounted) return;
    try {
      await context.read<Repository>().adjustStock(
            variant.id,
            value,
            reason.text.trim().isEmpty ? 'Ajustement manuel' : reason.text.trim(),
          );
      if (!mounted) return;
      showMessage(context, 'Stock mis à jour.');
      await _refresh();
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  Future<void> _togglePublished(Product product, bool publish) async {
    try {
      await context.read<Repository>().toggleProductPublished(product.id, publish);
      await _refresh();
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Articles')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: TextField(
              controller: _search,
              onSubmitted: (_) => _refresh(),
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Rechercher un article',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.arrow_forward),
                  onPressed: _refresh,
                ),
              ),
            ),
          ),
          Expanded(
            child: FutureBuilder<List<Product>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  final error = snapshot.error;
                  return ErrorView(
                    message: error is ApiException ? error.message : 'Erreur inattendue.',
                    onRetry: _refresh,
                  );
                }
                final products = snapshot.data ?? [];
                if (products.isEmpty) {
                  return const EmptyState(
                    icon: Icons.inventory_2_outlined,
                    title: 'Aucun article',
                  );
                }
                return RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    itemCount: products.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final product = products[index];
                      final stock = product.variants.fold<int>(0, (sum, v) => sum + v.stockQty);
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            ProductThumb(url: product.imageUrl, size: 60),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    product.name,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    '${money(product.price)} · stock $stock',
                                    style: const TextStyle(fontSize: 12.5, color: KsgColors.muted),
                                  ),
                                  Row(
                                    children: [
                                      TextButton(
                                        onPressed: () => _adjustStock(product),
                                        child: const Text('Stock'),
                                      ),
                                      TextButton(
                                        onPressed: () => _togglePublished(product, !product.isPublished),
                                        child: Text(product.isPublished ? 'Retirer' : 'Mettre en ligne'),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

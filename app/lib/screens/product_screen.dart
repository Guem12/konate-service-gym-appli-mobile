import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/api_client.dart';
import '../api/repository.dart';
import '../core/format.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import '../state/cart_state.dart';

class ProductScreen extends StatefulWidget {
  const ProductScreen({super.key, required this.productId});

  final int productId;

  @override
  State<ProductScreen> createState() => _ProductScreenState();
}

class _ProductScreenState extends State<ProductScreen> {
  final _scaffoldKey = GlobalKey<ScaffoldState>();
  Product? _product;
  ProductVariant? _variant;
  bool _loading = true;
  String? _error;
  int _quantity = 1;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final product = await context.read<Repository>().product(widget.productId);
      if (!mounted) return;
      ProductVariant? preselected;
      for (final variant in product.variants) {
        if (variant.inStock) {
          preselected = variant;
          break;
        }
      }
      setState(() {
        _product = product;
        _variant = preselected ?? (product.variants.isNotEmpty ? product.variants.first : null);
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addToCart() async {
    final variant = _variant;
    if (variant == null) {
      showMessage(context, 'Cet article est indisponible.');
      return;
    }
    final error = await context.read<CartState>().add(variant.id, quantity: _quantity);
    if (!mounted) return;
    showMessage(context, error ?? 'Ajouté au panier.');
  }

  Future<void> _toggleFavorite() async {
    final product = _product;
    if (product == null) return;
    try {
      final isFavorite = await context.read<Repository>().toggleFavorite(product.id);
      if (!mounted) return;
      setState(() => _product = _withFavorite(product, isFavorite));
      showMessage(context, isFavorite ? 'Ajouté à vos favoris.' : 'Retiré des favoris.');
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  Product _withFavorite(Product product, bool isFavorite) => Product(
        id: product.id,
        name: product.name,
        slug: product.slug,
        price: product.price,
        comparePrice: product.comparePrice,
        imageUrl: product.imageUrl,
        categoryId: product.categoryId,
        categoryName: product.categoryName,
        brandName: product.brandName,
        description: product.description,
        stockStatus: product.stockStatus,
        status: product.status,
        isFavorite: isFavorite,
        isNew: product.isNew,
        warrantyMonths: product.warrantyMonths,
        variants: product.variants,
        images: product.images,
        characteristics: product.characteristics,
      );

  Future<void> _whatsapp() async {
    final product = _product;
    if (product == null) return;
    try {
      final url = await context
          .read<Repository>()
          .whatsappLink(productId: product.id, variantId: _variant?.id);
      if (url.isEmpty) return;
      if (!await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication) && mounted) {
        showMessage(context, 'Impossible d\'ouvrir WhatsApp.');
      }
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final product = _product;
    return Scaffold(
      key: _scaffoldKey,
      appBar: AppBar(
        title: Text(product?.name ?? 'Produit', maxLines: 1),
        actions: [
          if (product != null)
            IconButton(
              onPressed: _toggleFavorite,
              tooltip: 'Favori',
              icon: Icon(
                product.isFavorite ? Icons.favorite : Icons.favorite_border,
                color: product.isFavorite ? KsgColors.red : null,
              ),
            ),
        ],
      ),
      body: _body(),
      bottomNavigationBar: product == null ? null : _bottomBar(product),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return ErrorView(message: _error!, onRetry: _load);
    final product = _product!;
    final gallery = product.images.isNotEmpty
        ? product.images
        : [if (product.imageUrl != null) product.imageUrl!];

    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        if (gallery.isNotEmpty)
          SizedBox(
            height: 280,
            child: PageView.builder(
              itemCount: gallery.length,
              itemBuilder: (context, index) => ProductThumb(
                url: gallery[index],
                size: double.infinity,
                radius: 0,
                iconSize: 64,
              ),
            ),
          )
        else
          Container(
            height: 240,
            color: const Color(0xFFEDE8DC),
            child: const Icon(Icons.fitness_center, size: 64, color: KsgColors.muted),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (product.categoryName.isNotEmpty)
                Text(
                  product.categoryName.toUpperCase(),
                  style: const TextStyle(
                    fontSize: 11,
                    letterSpacing: 1.1,
                    fontWeight: FontWeight.w700,
                    color: KsgColors.muted,
                  ),
                ),
              const SizedBox(height: 6),
              Text(
                product.name,
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, height: 1.2),
              ),
              const SizedBox(height: 10),
              PriceTag(product: product, fontSize: 22),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  StatusChip(
                    label: product.inStock ? 'En stock' : 'Rupture',
                    status: product.inStock ? 'delivered' : 'cancelled',
                  ),
                  if (product.warrantyMonths > 0)
                    StatusChip(label: 'Garantie ${product.warrantyMonths} mois', status: 'shipping'),
                  if (product.isNew) const StatusChip(label: 'Nouveau', status: 'shipping'),
                ],
              ),
              if (product.variants.isNotEmpty) ...[
                const SizedBox(height: 20),
                const Text('Choisissez la variante', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final variant in product.variants)
                      ChoiceChip(
                        label: Text(
                          variant.inStock
                              ? '${variant.label} · ${money(variant.price)}'
                              : '${variant.label} (rupture)',
                        ),
                        selected: _variant?.id == variant.id,
                        onSelected: variant.inStock
                            ? (_) => setState(() {
                                  _variant = variant;
                                  _quantity = 1;
                                })
                            : null,
                      ),
                  ],
                ),
              ],
              if (product.description.isNotEmpty) ...[
                const SizedBox(height: 22),
                const Text('Description', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                const SizedBox(height: 8),
                Text(
                  product.description,
                  style: const TextStyle(height: 1.5, color: KsgColors.ink),
                ),
              ],
              if (product.characteristics.isNotEmpty) ...[
                const SizedBox(height: 20),
                const Text('Caractéristiques', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                const SizedBox(height: 8),
                for (final line in product.characteristics)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.check_circle_outline, size: 18, color: KsgColors.green),
                        const SizedBox(width: 8),
                        Expanded(child: Text(line, style: const TextStyle(height: 1.4))),
                      ],
                    ),
                  ),
              ],
              if (!product.inStock) ...[
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF4D6),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text(
                    'Article en rupture. Contactez-nous sur WhatsApp pour connaître la date de réapprovisionnement.',
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _bottomBar(Product product) {
    final variant = _variant;
    final available = variant != null && variant.inStock;
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(top: BorderSide(color: Color(0xFFEFEBE0))),
        ),
        child: Row(
          children: [
            if (available)
              Container(
                decoration: BoxDecoration(
                  border: Border.all(color: const Color(0xFFE3DFD3)),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      onPressed: _quantity > 1 ? () => setState(() => _quantity--) : null,
                      icon: const Icon(Icons.remove, size: 18),
                    ),
                    Text('$_quantity', style: const TextStyle(fontWeight: FontWeight.w700)),
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      onPressed: _quantity < variant.stockQty
                          ? () => setState(() => _quantity++)
                          : null,
                      icon: const Icon(Icons.add, size: 18),
                    ),
                  ],
                ),
              ),
            if (available) const SizedBox(width: 10),
            Expanded(
              child: FilledButton.icon(
                onPressed: available ? _addToCart : _whatsapp,
                icon: Icon(available ? Icons.add_shopping_cart : Icons.chat),
                label: Text(available ? 'Ajouter au panier' : 'Demander sur WhatsApp'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

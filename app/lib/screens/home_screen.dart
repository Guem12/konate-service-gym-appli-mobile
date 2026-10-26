import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state/auth_state.dart';

import '../api/api_client.dart';
import '../api/repository.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import 'catalog_screen.dart';
import 'product_screen.dart';
import 'profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<HomeData> _future;
  ShopSettings? _settings;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<HomeData> _load() async {
    final repository = context.read<Repository>();
    final home = await repository.home();
    repository.settings().then((value) {
      if (mounted) setState(() => _settings = value);
    }).catchError((_) => null);
    return home;
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  void _openProduct(Product product) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => ProductScreen(productId: product.id)),
    );
  }

  Future<void> _contactWhatsApp() async {
    final phone = _settings?.whatsappPhone ?? '22382445807';
    final uri = Uri.parse('https://wa.me/$phone');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) &&
        mounted) {
      showMessage(context, 'WhatsApp n\'est pas disponible sur cet appareil.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: KsgColors.sand,
      body: RefreshIndicator(
        color: KsgColors.green,
        onRefresh: _refresh,
        child: FutureBuilder<HomeData>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(
                child: CircularProgressIndicator(color: KsgColors.green),
              );
            }
            if (snapshot.hasError) {
              final error = snapshot.error;
              return ErrorView(
                message: error is ApiException
                    ? error.message
                    : 'Vérifiez votre connexion.',
                onRetry: _refresh,
              );
            }
            final home = snapshot.data!;
            return CustomScrollView(
              slivers: [
                _sliverAppBar(),
                SliverToBoxAdapter(child: _hero(home)),
                SliverToBoxAdapter(child: _statsRow()),
                if (home.categories.isNotEmpty)
                  SliverToBoxAdapter(child: _categories(home.categories)),
                if (home.promotions.isNotEmpty)
                  SliverToBoxAdapter(
                    child: _productSection('Promotions 🔥', home.promotions),
                  ),
                if (home.popular.isNotEmpty)
                  SliverToBoxAdapter(
                    child: _productSection('Les plus vendus', home.popular),
                  ),
                if (home.newArrivals.isNotEmpty)
                  SliverToBoxAdapter(
                    child: _productSection('Nouveautés ✨', home.newArrivals),
                  ),
                if (_settings != null)
                  SliverToBoxAdapter(child: _shopInfo(_settings!)),
                const SliverToBoxAdapter(child: SizedBox(height: 32)),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _sliverAppBar() {
    return SliverAppBar(
      pinned: true,
      elevation: 0,
      backgroundColor: KsgColors.navy,
      expandedHeight: 0,
      toolbarHeight: 60,
      title: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          KsgLogoMonogram(size: 34),
          const SizedBox(width: 10),
          const Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Konaté-Service-Gym',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  'Matériel de gym • Bamako',
                  style: TextStyle(
                    color: KsgColors.muted,
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
      actions: [
        // ── Avatar de profil ──
        Consumer<AuthState>(
          builder: (context, auth, _) {
            final user = auth.user;
            final initials = user != null
                ? user.fullName
                    .split(' ')
                    .where((w) => w.isNotEmpty)
                    .take(2)
                    .map((w) => w[0].toUpperCase())
                    .join()
                : '?';
            return GestureDetector(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const ProfileScreen()),
              ),
              child: Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: KsgColors.green,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.3),
                    width: 2,
                  ),
                ),
                child: Center(
                  child: user != null
                      ? Text(
                          initials,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                            fontSize: 14,
                          ),
                        )
                      : const Icon(Icons.person, color: Colors.white, size: 20),
                ),
              ),
            );
          },
        ),
        const SizedBox(width: 14),
      ],
    );
  }

  Widget _hero(HomeData home) {
    final banner = home.banners.isNotEmpty ? home.banners.first : null;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [KsgColors.navy, Color(0xFF0A3828)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: KsgColors.green.withValues(alpha: 0.3)),
        boxShadow: [
          BoxShadow(
            color: KsgColors.navy.withValues(alpha: 0.4),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
            decoration: BoxDecoration(
              color: KsgColors.green.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(100),
              border: Border.all(color: KsgColors.green.withValues(alpha: 0.5)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6, height: 6,
                  decoration: const BoxDecoration(
                    color: KsgColors.green, shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                const Text(
                  'OFFRE DU MOMENT',
                  style: TextStyle(
                    color: KsgColors.green, fontSize: 11,
                    fontWeight: FontWeight.w800, letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Text(
            banner != null ? banner.title : 'Tout pour votre\nsalle de sport',
            style: const TextStyle(
              color: Colors.white, fontSize: 26, fontWeight: FontWeight.w900,
              height: 1.15, letterSpacing: -0.5,
            ),
          ),
          if (banner != null && banner.subtitle.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              banner.subtitle, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: Colors.white.withValues(alpha: 0.65), fontSize: 13),
            ),
          ],
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const CatalogScreen()),
                  ),
                  child: Container(
                    height: 46,
                    decoration: BoxDecoration(
                      color: KsgColors.green, borderRadius: BorderRadius.circular(14),
                    ),
                    alignment: Alignment.center,
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.grid_view_rounded, color: Colors.white, size: 18),
                        SizedBox(width: 8),
                        Text(
                          'Voir le catalogue',
                          style: TextStyle(
                            color: Colors.white, fontWeight: FontWeight.w700, fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              // Bouton WhatsApp avec le vrai logo
              GestureDetector(
                onTap: _contactWhatsApp,
                child: Container(
                  height: 46,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF25D366),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  alignment: Alignment.center,
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      FaIcon(FontAwesomeIcons.whatsapp, color: Colors.white, size: 16),
                      SizedBox(width: 8),
                      Text(
                        'WhatsApp',
                        style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statsRow() {
    final stats = [
      ('🏋️', 'Équipements', 'Pro & Amateurs'),
      ('🚚', 'Livraison', 'À Bamako'),
      ('⭐', 'Qualité', 'Garantie'),
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
      child: Row(
        children: stats.map((s) {
          return Expanded(
            child: Container(
              margin: EdgeInsets.only(
                right: stats.indexOf(s) < stats.length - 1 ? 10 : 0,
              ),
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
              decoration: BoxDecoration(
                color: KsgColors.surface,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: KsgColors.navy.withValues(alpha: 0.05),
                    blurRadius: 10, offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Text(s.$1, style: const TextStyle(fontSize: 22)),
                  const SizedBox(height: 4),
                  Text(s.$2, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11.5, color: KsgColors.textPrimary)),
                  Text(s.$3, style: const TextStyle(fontSize: 10, color: KsgColors.muted)),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _categories(List<Category> categories) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Catégories'),
        SizedBox(
          height: 116,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: categories.length,
            separatorBuilder: (_, _) => const SizedBox(width: 12),
            itemBuilder: (context, index) {
              final category = categories[index];
              return GestureDetector(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => CatalogScreen(
                      categoryId: category.id,
                      categoryName: category.name,
                    ),
                  ),
                ),
                child: Container(
                  width: 115,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: KsgColors.surface,
                    borderRadius: BorderRadius.circular(18),
                    boxShadow: [
                      BoxShadow(
                        color: KsgColors.navy.withValues(alpha: 0.06),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      ProductThumb(
                        url: category.imageUrl,
                        size: 46,
                        radius: 12,
                        iconSize: 22,
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            category.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: KsgColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${category.productCount} art.',
                            style: const TextStyle(
                              fontSize: 10.5,
                              color: KsgColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _productSection(String title, List<Product> products) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: title,
          action: 'Tout voir',
          onAction: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const CatalogScreen()),
          ),
        ),
        SizedBox(
          height: 265,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: products.length,
            separatorBuilder: (_, _) => const SizedBox(width: 12),
            itemBuilder: (context, index) {
              final product = products[index];
              return SizedBox(
                width: 172,
                child: ProductCard(product: product, onTap: () => _openProduct(product)),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _shopInfo(ShopSettings settings) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 24, 16, 0),
      decoration: BoxDecoration(
        color: KsgColors.navy,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: KsgColors.green.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 14),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.white.withValues(alpha: 0.08))),
            ),
            child: Row(
              children: [
                Container(
                  width: 36, height: 36,
                  decoration: BoxDecoration(
                    color: KsgColors.greenGlow, borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.storefront_rounded, color: KsgColors.green, size: 20),
                ),
                const SizedBox(width: 12),
                const Text('La boutique', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
            child: Column(
              children: [
                if (settings.address.isNotEmpty)
                  _infoRow(Icons.location_on_rounded, settings.address),
                if (settings.openingHours.isNotEmpty)
                  _infoRow(Icons.access_time_rounded, settings.openingHours),
                if (settings.deliveryNote.isNotEmpty)
                  _infoRow(Icons.local_shipping_rounded, settings.deliveryNote),
                if (settings.returnDelayDays > 0)
                  _infoRow(Icons.replay_rounded,
                      'Retour possible sous ${settings.returnDelayDays} jours'),
              ],
            ),
          ),
          // Bouton WhatsApp avec le vrai logo
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            child: GestureDetector(
              onTap: _contactWhatsApp,
              child: Container(
                height: 48,
                decoration: BoxDecoration(
                  color: const Color(0xFF25D366),
                  borderRadius: BorderRadius.circular(14),
                ),
                alignment: Alignment.center,
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    FaIcon(FontAwesomeIcons.whatsapp, color: Colors.white, size: 18),
                    SizedBox(width: 8),
                    Text(
                      'Commander par WhatsApp',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 14),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _infoRow(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: KsgColors.green),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: const TextStyle(fontSize: 13, color: Colors.white60, height: 1.4)),
          ),
        ],
      ),
    );
  }
}

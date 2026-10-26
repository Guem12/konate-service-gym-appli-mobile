import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../api/repository.dart';
import '../../models/models.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'product_screen.dart';

/// Écran catalogue avec pagination, filtres et recherche.
class CatalogScreen extends StatefulWidget {
  final int? categoryId;
  final String? categoryName;
  final String? searchQuery;
  final String? initialOrdering;

  const CatalogScreen({
    super.key,
    this.categoryId,
    this.categoryName,
    this.searchQuery,
    this.initialOrdering,
  });

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  late Repository _repository;
  String _search = '';
  String _ordering = '-sold_count';
  int _page = 1;
  int _totalCount = 0;
  bool _isLoading = true;
  bool _isLoadingMore = false;
  bool _hasError = false;
  String _errorMessage = '';
  final List<Product> _allProducts = [];
  late ScrollController _scrollController;

  @override
  void initState() {
    super.initState();
    _repository = Repository(ApiClient());
    _search = widget.searchQuery ?? '';
    _ordering = widget.initialOrdering ?? '-sold_count';
    _scrollController = ScrollController();
    _scrollController.addListener(_onScroll);
    _loadPage();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadPage() async {
    if (_isLoadingMore) return;

    setState(() {
      if (_page == 1) {
        _isLoading = true;
        _hasError = false;
      } else {
        _isLoadingMore = true;
      }
    });

    try {
      final result = await _repository.products(
        search: _search.isNotEmpty ? _search.trim() : '',
        categoryId: widget.categoryId,
        onlyPromotions: false,
        ordering: _ordering,
        page: _page,
      );

      setState(() {
        if (_page == 1) {
          _allProducts.clear();
        }
        _allProducts.addAll(result.products);
        _totalCount = result.count;
        _isLoading = false;
        _isLoadingMore = false;
      });
    } on ApiException catch (e) {
      setState(() {
        _hasError = true;
        _errorMessage = e.message;
        _isLoading = false;
        _isLoadingMore = false;
      });
    } catch (e) {
      setState(() {
        _hasError = true;
        _errorMessage = 'Erreur de chargement';
        _isLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  void _onScroll() {
    if (!_isLoadingMore &&
        !_isLoading &&
        _allProducts.length < _totalCount &&
        _scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent - 200) {
      _page++;
      _loadPage();
    }
  }

  Future<void> _refresh() async {
    setState(() {
      _page = 1;
      _search = widget.searchQuery ?? '';
      _ordering = '-sold_count';
    });
    await _loadPage();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildAppBar(),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _allProducts.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(color: KsgColors.green),
      );
    }
    if (_hasError && _allProducts.isEmpty) {
      return ErrorView(
        message: _errorMessage,
        onRetry: _refresh,
      );
    }
    return CustomScrollView(
      controller: _scrollController,
      slivers: [
        SliverAppBar(
          pinned: true,
          elevation: 0,
          backgroundColor: KsgColors.navy,
          expandedHeight: 0,
          automaticallyImplyLeading: false,
          title: Row(
            children: [
              KsgLogoMonogram(size: 30),
              const SizedBox(width: 8),
              const Flexible(
                child: Text(
                  'Konaté Service Gym',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.filter_list, color: Colors.white),
              onPressed: _showFilters,
            ),
            const SizedBox(width: 8),
          ],
        ),
        // Barre de recherche — enveloppée dans un SliverToBoxAdapter
        SliverToBoxAdapter(child: _buildSearchBar()),
        // Grille de produits
        if (_allProducts.isEmpty)
          const SliverFillRemaining(
            child: Center(
              child: Text(
                'Aucun produit trouvé.',
                style: TextStyle(color: KsgColors.muted, fontSize: 16),
              ),
            ),
          )
        else
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            sliver: SliverGrid(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final product = _allProducts[index];
                  return ProductCard(
                    product: product,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ProductScreen(productId: product.id),
                      ),
                    ),
                  );
                },
                childCount: _allProducts.length,
              ),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 160 / 240,
              ),
            ),
          ),
        // Indicateur de chargement en bas pour la pagination
        if (_isLoadingMore)
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.all(20),
              child: Center(
                child: CircularProgressIndicator(color: KsgColors.green),
              ),
            ),
          ),
        // Espace en bas
        const SliverToBoxAdapter(child: SizedBox(height: 24)),
      ],
    );
  }

  AppBar _buildAppBar() {
    return AppBar(
      backgroundColor: KsgColors.navy,
      foregroundColor: Colors.white,
      title: widget.categoryName != null
          ? Text(
              widget.categoryName!.contains('Promotions')
                  ? 'Promotions 🔥'
                  : widget.categoryName!.contains('Nouveautés')
                      ? 'Nouveautés ✨'
                      : widget.categoryName!.contains('Plus vendus')
                          ? 'Les plus vendus'
                          : 'Catégorie: ${widget.categoryName}',
              style: const TextStyle(fontSize: 18),
            )
          : const Text(
              'Catalogue Konaté Service Gym',
              style: TextStyle(fontSize: 18),
            ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.all(12.0),
      child: TextField(
        onChanged: (value) {
          setState(() {
            _search = value;
            _page = 1;
          });
          _loadPage();
        },
        decoration: InputDecoration(
          hintText: 'Rechercher des produits...',
          prefixIcon: const Icon(Icons.search, color: KsgColors.muted),
          filled: true,
          fillColor: KsgColors.surface,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(20),
            borderSide: BorderSide.none,
          ),
        ),
      ),
    );
  }

  void _showFilters() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: KsgColors.navy,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Filtres',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 20),
              _buildFilterRow(
                label: 'Trier par',
                values: [
                  ('Prix croissant', 'price'),
                  ('Prix décroissant', '-price'),
                  ('Plus vendus', '-sold_count'),
                  ('Nouveautés', '-created_at'),
                ],
                selected: _ordering,
                onChanged: (val) {
                  setState(() {
                    _ordering = val;
                    _page = 1;
                  });
                  _loadPage();
                  Navigator.of(context).pop();
                },
              ),
              const SizedBox(height: 12),
              _buildFilterRow(
                label: 'Disponibilité',
                values: [
                  ('En stock', 'in_stock'),
                  ('Rupture', 'out_of_stock'),
                ],
                selected: '',
                onChanged: (val) {
                  Navigator.of(context).pop();
                },
              ),
              const SizedBox(height: 12),
              _buildFilterRow(
                label: 'Promotion',
                values: [
                  ('Tout', ''),
                  ('Promos uniquement', 'promotion'),
                ],
                selected: '',
                onChanged: (val) {
                  setState(() {
                    _page = 1;
                  });
                  _loadPage();
                  Navigator.of(context).pop();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFilterRow({
    required String label,
    required List<(String, String)> values,
    required String selected,
    required ValueChanged<String> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: KsgColors.muted,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 8,
            children: List<Widget>.generate(values.length, (index) {
              final (label, value) = values[index];
              final isSelected = selected == value;
              return FilterChip(
                label: Text(
                  label,
                  style: TextStyle(
                    color: isSelected ? Colors.white : KsgColors.muted,
                    fontSize: 11,
                  ),
                ),
                selected: isSelected,
                selectedColor: KsgColors.green,
                onSelected: (selected) => onChanged(value),
              );
            }),
          ),
        ],
      ),
    );
  }
}
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/repository.dart';
import '../core/format.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import 'catalog_screen.dart';
import 'order_detail_screen.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  late Future<List<OrderSummary>> _future;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _future = context.read<Repository>().orders();
  }

  Future<void> _refresh() async {
    setState(() => _future = context.read<Repository>().orders());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes commandes'),
        actions: [
          IconButton(onPressed: _refresh, icon: const Icon(Icons.sync_rounded), tooltip: 'Actualiser'),
        ],
      ),
      body: FutureBuilder<List<OrderSummary>>(
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
          final all = snapshot.data ?? [];
          final orders = _filter == 'open' ? all.where((o) => o.isOpen).toList() : all;
          if (all.isEmpty) {
            return EmptyState(
              icon: Icons.receipt_long_outlined,
              title: 'Aucune commande',
              message: 'Vos commandes apparaîtront ici.',
              action: FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size(200, 48)),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const CatalogScreen()),
                ),
                child: const Text('Commencer mes achats'),
              ),
            );
          }
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Row(
                  children: [
                    ChoiceChip(
                      label: const Text('Toutes'),
                      selected: _filter == 'all',
                      onSelected: (_) => setState(() => _filter = 'all'),
                    ),
                    const SizedBox(width: 8),
                    ChoiceChip(
                      label: const Text('En cours'),
                      selected: _filter == 'open',
                      onSelected: (_) => setState(() => _filter = 'open'),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    itemCount: orders.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, index) => _tile(orders[index]),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _tile(OrderSummary order) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => OrderDetailScreen(orderId: order.id)),
      ),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ProductThumb(url: order.imageUrl, size: 64),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          order.number,
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                        ),
                      ),
                      StatusChip(label: order.statusLabel, status: order.status),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    order.itemNames.isEmpty ? '${order.itemCount} article(s)' : order.itemNames.join(', '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12.5, color: KsgColors.muted),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Text(
                        money(order.total),
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      const Spacer(),
                      Text(
                        shortDate(order.createdAt),
                        style: const TextStyle(fontSize: 11.5, color: KsgColors.muted),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

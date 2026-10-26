import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../api/repository.dart';
import '../../core/format.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';

class AdminOrdersScreen extends StatefulWidget {
  const AdminOrdersScreen({super.key});

  @override
  State<AdminOrdersScreen> createState() => _AdminOrdersScreenState();
}

class _AdminOrdersScreenState extends State<AdminOrdersScreen> {
  static const _filters = <String, String>{
    '': 'Toutes',
    'pending_payment': 'À vérifier',
    'confirmed': 'Confirmées',
    'preparing': 'En préparation',
    'shipping': 'En livraison',
    'delivered': 'Livrées',
  };

  late Future<List<OrderSummary>> _future;
  String _status = '';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<OrderSummary>> _load() => context.read<Repository>().adminOrders(status: _status);

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _changeStatus(OrderSummary order) async {
    final next = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      order.number,
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                    ),
                  ),
                  StatusChip(label: order.statusLabel, status: order.status),
                ],
              ),
            ),
            for (final entry in const {
              'confirmed': 'Confirmer la commande',
              'preparing': 'Passer en préparation',
              'shipping': 'Passer en livraison',
              'delivered': 'Marquer comme livrée',
              'cancelled': 'Annuler la commande',
            }.entries)
              ListTile(
                leading: Icon(
                  entry.key == 'cancelled' ? Icons.cancel_outlined : Icons.arrow_forward,
                  color: entry.key == 'cancelled' ? KsgColors.red : KsgColors.green,
                ),
                title: Text(entry.value),
                onTap: () => Navigator.pop(context, entry.key),
              ),
          ],
        ),
      ),
    );
    if (next == null || !mounted) return;
    try {
      await context.read<Repository>().updateOrderStatus(order.id, next);
      if (!mounted) return;
      showMessage(context, 'Statut mis à jour.');
      await _refresh();
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  Future<void> _exportPDFOrder(BuildContext context, int orderId) async {
    try {
      final repo = context.read<Repository>();
      final pdfBytes = await repo.exportPDF(type: 'orders', dateFrom: '', dateTo: '');
      // Note: This exports all orders with filters applied
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/commande-$orderId-${DateTime.now().millisecond}.pdf');
      await file.writeAsBytes(pdfBytes, flush: true);
      if (!mounted) return;
      await OpenFile.open(file.path);
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    } catch (e) {
      if (mounted) showMessage(context, 'Erreur inattendue: $e');
    }
  }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Commandes')),
      body: Column(
        children: [
          SizedBox(
            height: 46,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                for (final entry in _filters.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(entry.value),
                      selected: _status == entry.key,
                      onSelected: (_) {
                        setState(() => _status = entry.key);
                        _refresh();
                      },
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: FutureBuilder<List<OrderSummary>>(
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
                final orders = snapshot.data ?? [];
                if (orders.isEmpty) {
                  return const EmptyState(
                    icon: Icons.inbox_outlined,
                    title: 'Aucune commande',
                    message: 'Les nouvelles commandes apparaîtront ici.',
                  );
                }
                return RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    itemCount: orders.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final order = orders[index];
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    order.number,
                                    style: const TextStyle(fontWeight: FontWeight.w800),
                                  ),
                                ),
                                StatusChip(label: order.statusLabel, status: order.status),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${order.itemCount} article(s) · ${shortDate(order.createdAt)}',
                              style: const TextStyle(fontSize: 12, color: KsgColors.muted),
                            ),
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                Text(
                                  money(order.total),
                                  style: const TextStyle(fontWeight: FontWeight.w800),
                                ),
                                const SizedBox(width: 8),
                                if (order.balanceDue > 0)
                                  Text(
                                    'reste ${money(order.balanceDue)}',
                                    style: const TextStyle(fontSize: 12, color: KsgColors.red),
                                  ),
                                const Spacer(),
                                TextButton(
                                  onPressed: () => _changeStatus(order),
                                  child: const Text('Traiter'),
                                ),
                              ],
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  const Spacer(),
                                  FilledButton(
                                    onPressed: () => _exportPDFOrder(context, order.id),
                                    child: const Icon(Icons.remove_share, size: 16, color: Color(0xFF6B7280)),
                                    label: const Text('PDF', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600)),
                                    style: FilledButton.styleFrom(
                                      foregroundColor: const Color(0xFF6B7280),
                                      backgroundColor: const Color(0xFFF8FAFC),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                      textStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                              ],
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

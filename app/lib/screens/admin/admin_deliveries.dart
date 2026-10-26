import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../api/repository.dart';
import '../../core/format.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';
import '../../state/auth_state.dart';
import 'admin_payments.dart';

class AdminDeliveriesScreen extends StatefulWidget {
  const AdminDeliveriesScreen({super.key});

  @override
  State<AdminDeliveriesScreen> createState() => _AdminDeliveriesScreenState();
}

class _AdminDeliveriesScreenState extends State<AdminDeliveriesScreen> {
  late Future<List<Delivery>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<Repository>().deliveries();
  }

  Future<void> _refresh() async {
    setState(() => _future = context.read<Repository>().deliveries());
    await _future;
  }

  Future<void> _open(Delivery delivery) async {
    final courier = TextEditingController(text: delivery.courierName);
    final collected = TextEditingController(text: '${delivery.balanceDue}');
    final sheet = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          bottom: MediaQuery.of(context).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    delivery.orderNumber,
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                  ),
                ),
                StatusChip(label: delivery.statusLabel, status: delivery.status),
              ],
            ),
            const SizedBox(height: 8),
            Text('${delivery.customerName} · ${prettyPhone(delivery.customerPhone)}'),
            if (delivery.addressText.isNotEmpty) Text(delivery.addressText),
            if (delivery.slot.isNotEmpty) Text('Créneau : ${delivery.slot}'),
            const SizedBox(height: 14),
            TextField(
              controller: courier,
              decoration: const InputDecoration(labelText: 'Livreur'),
            ),
            const SizedBox(height: 12),
            if (!delivery.isDelivered)
              TextField(
                controller: collected,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Montant encaissé (FCFA)'),
              ),
            const SizedBox(height: 18),
            if (!delivery.isDelivered)
              FilledButton(
                onPressed: () => Navigator.pop(context, 'delivered'),
                child: const Text('Marquer livrée'),
              ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => Navigator.pop(context, 'in_transit'),
              child: const Text('En cours de livraison'),
            ),
          ],
        ),
      ),
    );
    if (sheet == null || !mounted) return;
    try {
      await context.read<Repository>().updateDelivery(delivery.id, {
        'status': sheet,
        if (courier.text.trim().isNotEmpty) 'courier_name': courier.text.trim(),
        if (sheet == 'delivered' && (int.tryParse(collected.text.trim()) ?? 0) > 0)
          'amount_collected': int.parse(collected.text.trim()),
      });
      if (!mounted) return;
      final collectedAmount = int.tryParse(collected.text.trim()) ?? 0;
      final isOwner = context.read<AuthState>().user?.isOwner ?? false;
      if (sheet == 'delivered' && collectedAmount > 0 && isOwner) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SnackBar(
              content: Text('${money(collectedAmount)} encaissés — à vérifier avant le reçu.'),
              action: SnackBarAction(
                label: 'Encaissements',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const AdminPaymentsScreen()),
                ),
              ),
            ),
          );
      } else {
        showMessage(context, 'Livraison mise à jour.');
      }
  }

  Future<void> _exportPDFDelivery(BuildContext context, Delivery delivery) async {
    try {
      final repo = context.read<Repository>();
      final pdfBytes = await repo.exportPDF(type: 'deliveries', dateFrom: '', dateTo: '');
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/livraison-${delivery.id}-${DateTime.now().millisecond}.pdf');
      await file.writeAsBytes(pdfBytes, flush: true);
      if (!mounted) return;
      await OpenFile.open(file.path);
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    } catch (e) {
      if (mounted) showMessage(context, 'Erreur inattendue: $e');
    }
  }
      await _refresh();
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Livraisons')),
      body: FutureBuilder<List<Delivery>>(
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
          final deliveries = snapshot.data ?? [];
          if (deliveries.isEmpty) {
            return const EmptyState(
              icon: Icons.delivery_dining,
              title: 'Aucune livraison',
              message: 'Les commandes avec livraison apparaîtront ici.',
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              itemCount: deliveries.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final delivery = deliveries[index];
                return InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: () => _open(delivery),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.local_shipping_outlined, color: KsgColors.green),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                delivery.orderNumber,
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                              Text(
                                '${delivery.customerName} · ${delivery.zone.isEmpty ? delivery.addressText : delivery.zone}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12.5, color: KsgColors.muted),
                              ),
                              if (delivery.courierName.isNotEmpty)
                                Text(
                                  'Livreur : ${delivery.courierName}',
                                  style: const TextStyle(fontSize: 12, color: KsgColors.muted),
                                ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            StatusChip(label: delivery.statusLabel, status: delivery.status),
                            const SizedBox(height: 6),
                            Text(
                              money(delivery.balanceDue),
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

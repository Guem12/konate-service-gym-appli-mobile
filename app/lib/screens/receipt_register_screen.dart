import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/repository.dart';
import '../core/format.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import '../screens/order_detail_screen.dart';
import '../screens/catalog_screen.dart';

class ReceiptRegisterScreen extends StatefulWidget {
  const ReceiptRegisterScreen({super.key});

  @override
  State<ReceiptRegisterScreen> createState() => _ReceiptRegisterScreenState();
}

class _ReceiptRegisterScreenState extends State<ReceiptRegisterScreen> {
  late Future<List<OrderSummary>> _future;
  String _filterClient = '';
  String _filterDateFrom = '';
  String _filterDateTo = '';
  String _filterPaymentStatus = 'all';
  String _filterKind = 'all';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<OrderSummary>> _load() async {
    final repository = context.read<Repository>();
    return repository.ordersReceiptRegister(
      clientFilter: _filterClient.isEmpty ? null : _filterClient,
      dateFrom: _filterDateFrom.isEmpty ? null : _filterDateFrom,
      dateTo: _filterDateTo.isEmpty ? null : _filterDateTo,
      paymentStatus: _filterPaymentStatus == 'all' ? null : _filterPaymentStatus,
      kind: _filterKind == 'all' ? null : _filterKind,
    );
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Registre des reçus'),
        actions: [
          IconButton(
            onPressed: _refresh,
            icon: const Icon(Icons.sync_rounded),
            tooltip: 'Actualiser',
          ),
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
          final filtered = _applyFilters(all);

          if (all.isEmpty && _filterClient.isEmpty && _filterDateFrom.isEmpty &&
              _filterDateTo.isEmpty && _filterPaymentStatus == 'all' && _filterKind == 'all') {
            return EmptyState(
              icon: Icons.receipt_long_outlined,
              title: 'Aucun reçu',
              message: 'Vos reçus apparaîtront ici.',
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
              // Filtres section
              _buildFiltersSection(),

              Expanded(
                child: RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    itemCount: filtered.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, index) => _tile(filtered[index]),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  List<OrderSummary> _applyFilters(List<OrderSummary> all) {
    return all.where((order) {
      // Filtre par client (nom ou numéro de commande)
      if (_filterClient.isNotEmpty) {
        final searchLower = _filterClient.toLowerCase();
        if (!order.number.toLowerCase().contains(searchLower) &&
            !order.itemNames.any((name) => name.toLowerCase().contains(searchLower))) {
          return false;
        }
      }

      // Filtre par date
      if (_filterDateFrom.isNotEmpty || _filterDateTo.isNotEmpty) {
        final orderDate = order.createdAt;
        if (_filterDateFrom.isNotEmpty && orderDate != null &&
            orderDate.isBefore(DateTime.parse(_filterDateFrom))) {
          return false;
        }
        if (_filterDateTo.isNotEmpty && orderDate != null &&
            orderDate.isAfter(DateTime.parse(_filterDateTo))) {
          return false;
        }
      }

      // Filtre par statut de paiement
      if (_filterPaymentStatus == 'unpaid' && order.amountPaid <= 0 &&
          order.balanceDue > 0) {
        // Keep unpaid orders
      } else if (_filterPaymentStatus == 'paid' && order.balanceDue <= 0) {
        // Keep paid orders
      } else if (_filterPaymentStatus == 'partial' &&
          !(order.amountPaid > 0 && order.balanceDue > 0)) {
        return false;
      }

      // Filtre par type de document (receipt vs invoice)
      if (_filterKind == 'receipt' && order.amountPaid <= 0) {
        return false;
      }
      if (_filterKind == 'invoice' && order.amountPaid <= 0) {
        // Invoices can also have 0 payment, but let's keep them
      }

      return true;
    }).toList();
  }

  Widget _buildFiltersSection() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Column(
        children: [
          // Filtre par client
          TextField(
            decoration: InputDecoration(
              labelText: 'Client / n° commande',
              prefixIcon: const Icon(Icons.person_outline),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            ),
            onChanged: (value) {
              setState(() => _filterClient = value);
            },
          ),
          const SizedBox(height: 12),

          // Filtres rangés horizontalement
          Row(
            children: [
              // Filtre par date début
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    labelText: 'Date début',
                    prefixIcon: const Icon(Icons.calendar_today),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  ),
                  onChanged: (value) {
                    setState(() => _filterDateFrom = value);
                  },
                  enableSuggestions: true,
                  textInputAction: TextInputAction.done,
                ),
              ),
              const SizedBox(width: 12),
              // Filtre par date fin
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    labelText: 'Date fin',
                    prefixIcon: const Icon(Icons.calendar_today),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  ),
                  onChanged: (value) {
                    setState(() => _filterDateTo = value);
                  },
                  enableSuggestions: true,
                  textInputAction: TextInputAction.done,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Filtre par statut de paiement
          DropdownButtonFormField<String>(
            initialValue: _filterPaymentStatus == 'all' ? null : _filterPaymentStatus,
            decoration: InputDecoration(
              labelText: 'Statut paiement',
              prefixIcon: const Icon(Icons.payment_outlined),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            ),
            items: const [
              DropdownMenuItem(value: 'all', child: Text('Tous')),
              DropdownMenuItem(value: 'unpaid', child: Text('Non payé')),
              DropdownMenuItem(value: 'partial', child: Text('Partiel')),
              DropdownMenuItem(value: 'paid', child: Text('Payé')),
            ],
            onChanged: (value) {
              setState(() => _filterPaymentStatus = value ?? 'all');
            },
          ),
          const SizedBox(height: 12),

          // Filtre par type de document
          DropdownButtonFormField<String>(
            initialValue: _filterKind == 'all' ? null : _filterKind,
            decoration: InputDecoration(
              labelText: 'Type de document',
              prefixIcon: const Icon(Icons.description_outlined),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            ),
            items: const [
              DropdownMenuItem(value: 'all', child: Text('Tous')),
              DropdownMenuItem(value: 'receipt', child: Text('Réçus')),
              DropdownMenuItem(value: 'invoice', child: Text('Factures')),
            ],
            onChanged: (value) {
              setState(() => _filterKind = value ?? 'all');
            },
          ),
          const SizedBox(height: 24),
        ],
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
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Icone selon le type
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: KsgColors.green.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                order.amountPaid > 0
                    ? Icons.receipt_long_rounded
                    : Icons.receipt,
                color: KsgColors.green,
                size: 28,
              ),
            ),
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
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      StatusChip(
                        label: order.statusLabel,
                        status: order.status,
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    order.itemNames.isEmpty
                        ? '${order.itemCount} article(s)'
                        : order.itemNames.join(', '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 12.5,
                      color: KsgColors.muted,
                    ),
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
                        style: const TextStyle(
                          fontSize: 11.5,
                          color: KsgColors.muted,
                        ),
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
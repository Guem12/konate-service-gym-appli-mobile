import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/api_client.dart';
import '../api/repository.dart';
import '../core/format.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import '../services/receipt_service.dart';

class OrderDetailScreen extends StatefulWidget {
  const OrderDetailScreen({super.key, required this.orderId, this.initial});

  final int orderId;
  final OrderDetail? initial;

  @override
  State<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends State<OrderDetailScreen> {
  OrderDetail? _order;
  bool _loading = true;
  bool _sharing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _order = widget.initial;
    _load();
  }

  Future<void> _load() async {
    try {
      final order = await context.read<Repository>().order(widget.orderId);
      if (mounted) setState(() => _order = order);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _cancel() async {
    final reason = await showDialog<String>(
      context: context,
      builder: (context) => const _CancelDialog(),
    );
    if (reason == null || !mounted) return;
    try {
      await context.read<Repository>().cancelOrder(widget.orderId, reason);
      if (!mounted) return;
      showMessage(context, 'Commande annulée.');
      await _load();
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  /// Télécharge le reçu PDF puis ouvre la feuille de partage (WhatsApp, e-mail…).
  Future<void> _shareReceipt() async {
    final order = _order;
    if (order == null) return;
    if (kIsWeb) {
      showMessage(context, 'Le partage du reçu se fait depuis l\'application mobile.');
      return;
    }
    setState(() => _sharing = true);
    try {
      await context.read<ReceiptService>().share(
            orderId: order.id,
            orderLabel: order.number,
            customerName: order.customerName,
          );
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    } on Exception {
      if (mounted) showMessage(context, 'Partage impossible sur cet appareil.');
    } finally {
      if (mounted) setState(() => _sharing = false);
    }
  }

  Future<void> _whatsapp() async {
    final url = _order?.whatsappUrl ?? '';
    if (url.isEmpty) {
      showMessage(context, 'Lien WhatsApp indisponible.');
      return;
    }
    if (!await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication) && mounted) {
      showMessage(context, 'Impossible d\'ouvrir WhatsApp.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = _order;
    return Scaffold(
      appBar: AppBar(
        title: Text(order?.number ?? 'Commande'),
        actions: [
          IconButton(onPressed: _whatsapp, icon: const Icon(Icons.chat_outlined)),
        ],
      ),
      body: _loading && order == null
          ? const Center(child: CircularProgressIndicator())
          : _error != null && order == null
              ? ErrorView(message: _error!, onRetry: _load)
              : _content(order!),
      bottomNavigationBar: order != null && (order.canCancel || order.amountPaid > 0)
          ? _actionBar(order)
          : null,
    );
  }

  Widget _content(OrderDetail order) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    StatusChip(label: order.statusLabel, status: order.status),
                    const Spacer(),
                    Text(shortDate(order.createdAt), style: const TextStyle(color: KsgColors.muted)),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  money(order.total),
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                if (order.balanceDue > 0)
                  Text(
                    'Reste à payer : ${money(order.balanceDue)}',
                    style: const TextStyle(color: KsgColors.red, fontWeight: FontWeight.w600),
                  )
                else
                  const Text(
                    'Commande soldée',
                    style: TextStyle(color: KsgColors.green, fontWeight: FontWeight.w600),
                  ),
                if (order.deliveryAddress.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.place_outlined, size: 18, color: KsgColors.muted),
                      const SizedBox(width: 8),
                      Expanded(child: Text(order.deliveryAddress)),
                    ],
                  ),
                ],
                if (order.deliverySlot.isNotEmpty)
                  Row(
                    children: [
                      const Icon(Icons.schedule, size: 18, color: KsgColors.muted),
                      const SizedBox(width: 8),
                      Text('Créneau : ${order.deliverySlot}'),
                    ],
                  ),
              ],
            ),
          ),
          const SectionHeader(title: 'Articles'),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
            child: Column(
              children: [
                for (final line in order.lines)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(line.productName, style: const TextStyle(fontWeight: FontWeight.w600)),
                              if (line.variantLabel.isNotEmpty)
                                Text(
                                  line.variantLabel,
                                  style: const TextStyle(fontSize: 12, color: KsgColors.muted),
                                ),
                            ],
                          ),
                        ),
                        Text('${line.quantity} × ${money(line.unitPrice)}'),
                      ],
                    ),
                  ),
                const Divider(height: 20),
                if (order.discount > 0)
                  _row('Remise', '- ${money(order.discount)}'),
                _row('Sous-total', money(order.subtotal)),
                _row('Total', money(order.total), bold: true),
              ],
            ),
          ),
          if (order.timeline.isNotEmpty) ...[
            const SectionHeader(title: 'Suivi'),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
              child: Column(
                children: [
                  for (final entry in order.timeline)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.circle, size: 8, color: KsgColors.green),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(entry.label, style: const TextStyle(fontWeight: FontWeight.w600)),
                                if (entry.note.isNotEmpty)
                                  Text(
                                    entry.note,
                                    style: const TextStyle(fontSize: 12.5, color: KsgColors.muted),
                                  ),
                              ],
                            ),
                          ),
                          Text(
                            longDate(entry.createdAt),
                            style: const TextStyle(fontSize: 11, color: KsgColors.muted),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ],
          if (order.whatsappUrl.isNotEmpty) ...[
            const SizedBox(height: 18),
            OutlinedButton.icon(
              onPressed: _whatsapp,
              icon: const Icon(Icons.chat),
              label: const Text('Suivre sur WhatsApp'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _row(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(value, style: TextStyle(fontWeight: bold ? FontWeight.w800 : FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _actionBar(OrderDetail order) {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(top: BorderSide(color: Color(0xFFEFEBE0))),
        ),
        child: Row(
          children: [
            if (order.canCancel)
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _cancel,
                  icon: const Icon(Icons.cancel_outlined, size: 18),
                  label: const Text('Annuler'),
                ),
              ),
            if (order.canCancel && order.amountPaid > 0) const SizedBox(width: 10),
            if (order.amountPaid > 0)
              Expanded(
                child: FilledButton.icon(
                  onPressed: _sharing ? null : _shareReceipt,
                  icon: _sharing
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.receipt_long, size: 18),
                  label: Text(_sharing ? 'Préparation…' : 'Partager le reçu'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _CancelDialog extends StatefulWidget {
  const _CancelDialog();

  @override
  State<_CancelDialog> createState() => _CancelDialogState();
}

class _CancelDialogState extends State<_CancelDialog> {
  final _reason = TextEditingController();

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Annuler la commande'),
      content: TextField(
        controller: _reason,
        maxLines: 2,
        decoration: const InputDecoration(labelText: 'Motif'),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Retour')),
        FilledButton(
          onPressed: () => Navigator.pop(context, _reason.text.trim().isEmpty ? 'Annulée par le client' : _reason.text.trim()),
          child: const Text('Confirmer'),
        ),
      ],
    );
  }
}

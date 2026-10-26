import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../api/repository.dart';
import '../../core/format.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';
import '../../services/receipt_service.dart';

/// Encaissements en attente de vérification, puis partage du reçu au client.
class AdminPaymentsScreen extends StatefulWidget {
  const AdminPaymentsScreen({super.key});

  @override
  State<AdminPaymentsScreen> createState() => _AdminPaymentsScreenState();
}

class _AdminPaymentsScreenState extends State<AdminPaymentsScreen> {
  late Future<({int count, int total, List<PaymentInfo> results})> _future;
  int? _busyId;

  @override
  void initState() {
    super.initState();
    _future = context.read<Repository>().pendingPayments();
  }

  Future<void> _refresh() async {
    setState(() => _future = context.read<Repository>().pendingPayments());
    await _future;
  }

  Future<void> _confirm(PaymentInfo payment) async {
    setState(() => _busyId = payment.id);
    try {
      final confirmed = await context.read<Repository>().confirmPayment(payment.id);
      if (!mounted) return;
      setState(() => _busyId = null);
      showMessage(context, 'Encaissement confirmé pour ${confirmed.orderNumber}.');
      await _refresh();
      if (!mounted) return;
      await _offerReceipt(confirmed);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _busyId = null);
      showMessage(context, e.message);
    }
  }

  /// Propose immédiatement le partage WhatsApp du reçu qui vient d'être soldé.
  Future<void> _offerReceipt(PaymentInfo payment) async {
    if (kIsWeb) return;
    final share = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reçu de vente'),
        content: Text(
          'Le paiement de ${money(payment.amount)} pour ${payment.orderNumber} est confirmé.\n\n'
          'Partager le reçu au client maintenant ?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Plus tard')),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Partager'),
          ),
        ],
      ),
    );
    if (share != true || !mounted) return;
    try {
      await context.read<ReceiptService>().share(
            orderId: payment.orderId,
            orderLabel: payment.orderNumber,
            customerName: payment.customerName,
          );
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    } on Exception {
      if (mounted) showMessage(context, 'Partage impossible sur cet appareil.');
    }
  }

  Future<void> _shareOnly(PaymentInfo payment) async {
    try {
      await context.read<ReceiptService>().share(
            orderId: payment.orderId,
            orderLabel: payment.orderNumber,
            customerName: payment.customerName,
          );
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    } on Exception {
      if (mounted) showMessage(context, 'Partage impossible sur cet appareil.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Encaissements'),
        actions: [IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh))],
      ),
      body: FutureBuilder<({int count, int total, List<PaymentInfo> results})>(
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
          final data = snapshot.data!;
          if (data.results.isEmpty) {
            return const EmptyState(
              icon: Icons.verified_outlined,
              title: 'Tout est vérifié',
              message: 'Aucun encaissement en attente de confirmation.',
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.pending_actions, color: KsgColors.gold),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          '${data.count} paiement(s) à vérifier',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      Text(
                        money(data.total),
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                for (final payment in data.results) _tile(payment),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _tile(PaymentInfo payment) {
    final busy = _busyId == payment.id;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  payment.orderNumber,
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
              StatusChip(label: payment.statusLabel, status: 'pending_payment'),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            [
              payment.customerName,
              payment.methodLabel,
              if (payment.reference.isNotEmpty) 'Réf. ${payment.reference}',
            ].where((e) => e.isNotEmpty).join(' · '),
            style: const TextStyle(fontSize: 12.5, color: KsgColors.muted),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Text(
                money(payment.amount),
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
              ),
              const Spacer(),
              if (payment.createdAt != null)
                Text(
                  shortDate(payment.createdAt),
                  style: const TextStyle(fontSize: 11.5, color: KsgColors.muted),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton.icon(
                onPressed: busy ? null : () => _shareOnly(payment),
                icon: const Icon(Icons.receipt_long, size: 18),
                label: const Text('Reçu'),
              ),
              const SizedBox(width: 6),
              FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size(120, 42)),
                onPressed: busy ? null : () => _confirm(payment),
                child: Text(busy ? 'Confirmation…' : 'Confirmer'),
              ),
            ],
          ),
          const SizedBox(width: 6),
          FilledButton(
            onPressed: busy ? null : () => _exportPDFPayment(context, payment.id),
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
    );
  }
}

  Future<void> _exportPDFPayment(BuildContext context, int paymentId) async {
    try {
      final repo = context.read<Repository>();
      final pdfBytes = await repo.exportPDF(type: 'payments', dateFrom: '', dateTo: '');
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/encaissement-$paymentId-${DateTime.now().millisecond}.pdf');
      await file.writeAsBytes(pdfBytes, flush: true);
      if (!mounted) return;
      await OpenFile.open(file.path);
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    } catch (e) {
      if (mounted) showMessage(context, 'Erreur inattendue: $e');
    }
  }

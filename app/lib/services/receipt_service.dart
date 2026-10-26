import 'dart:typed_data';

import 'package:share_plus/share_plus.dart';

import '../api/api_client.dart';
import 'receipt_file.dart';

/// Prépare et partage le reçu de vente (PDF) d'une commande encaissée.
///
/// L'écriture du fichier et le partage sont injectables pour rester testables
/// sans plugin ni système de fichiers.
class ReceiptService {
  ReceiptService(
    this.api, {
    Future<String> Function(String fileName, Uint8List bytes)? writer,
    Future<void> Function(String path, String text, String subject)? sharer,
  })  : _write = writer ?? writeReceiptFile,
        _share = sharer ?? _shareWithSystem;

  final ApiClient api;
  final Future<String> Function(String fileName, Uint8List bytes) _write;
  final Future<void> Function(String path, String text, String subject) _share;

  /// Récupère le reçu côté API. Lève une [ApiException] si aucun encaissement
  /// n'a encore été enregistré sur la commande.
  Future<({Uint8List bytes, String fileName})> download(int orderId) async {
    final bytes = await api.getBytes(
      '/orders/$orderId/invoice',
      query: {'kind': 'receipt'},
    );
    if (bytes.isEmpty) {
      throw ApiException('Le reçu est vide. Réessayez dans un instant.');
    }
    return (bytes: bytes, fileName: 'recu-$orderId.pdf');
  }

  /// Télécharge le reçu puis ouvre la feuille de partage du système
  /// (WhatsApp, e-mail, enregistrement…). Renvoie le chemin du fichier partagé.
  Future<String> share({
    required int orderId,
    String orderLabel = '',
    String customerName = '',
  }) async {
    final receipt = await download(orderId);
    final path = await _write(receipt.fileName, receipt.bytes);
    final text = [
      'Reçu de vente${orderLabel.isEmpty ? '' : ' $orderLabel'} — Konaté-Service-Gym',
      if (customerName.isNotEmpty) 'Client : $customerName',
      'Merci de votre confiance.',
    ].join('\n');
    await _share(path, text, 'Reçu $orderLabel');
    return path;
  }

  static Future<void> _shareWithSystem(String path, String text, String subject) async {
    await Share.share(
      text,
      subject: subject,
    );
  }
}

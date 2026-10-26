import 'dart:typed_data';

/// Sur le web et les plateformes sans système de fichiers, le partage de PDF
/// n'est pas disponible : le reçu reste consultable via la facture de l'API.
Future<String> writeReceiptFile(String fileName, Uint8List bytes) {
  throw UnsupportedError(
    'Le partage de fichier n\'est pas disponible sur cette plateforme.',
  );
}

import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

/// Écrit le reçu dans le dossier temporaire de l'application et renvoie son chemin.
Future<String> writeReceiptFile(String fileName, Uint8List bytes) async {
  final directory = await getTemporaryDirectory();
  final file = File('${directory.path}/$fileName');
  await file.writeAsBytes(bytes, flush: true);
  return file.path;
}

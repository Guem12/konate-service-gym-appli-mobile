import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:konate_gym/api/api_client.dart';
import 'package:konate_gym/services/receipt_service.dart';

/// Client factice : renvoie un PDF minimal ou l'erreur demandée.
class _FakeApi extends ApiClient {
  _FakeApi({this.bytes, this.error});

  final Uint8List? bytes;
  final ApiException? error;
  String? lastPath;
  Map<String, dynamic>? lastQuery;

  @override
  Future<Uint8List> getBytes(String path, {Map<String, dynamic>? query}) async {
    lastPath = path;
    lastQuery = query;
    if (error != null) throw error!;
    return bytes ?? Uint8List.fromList(utf8.encode('%PDF-1.4'));
  }
}

void main() {
  test('le reçu est téléchargé en PDF puis écrit sur le disque', () async {
    final api = _FakeApi(bytes: Uint8List.fromList(utf8.encode('%PDF-1.4 reçu')));
    String? writtenName;
    Uint8List? writtenBytes;

    final service = ReceiptService(
      api,
      writer: (name, content) async {
        writtenName = name;
        writtenBytes = content;
        return '/tmp/$name';
      },
      sharer: (path, text, subject) async {},
    );

    final receipt = await service.download(42);
    expect(api.lastPath, '/orders/42/invoice');
    expect(api.lastQuery, {'kind': 'receipt'});
    expect(receipt.fileName, 'recu-42.pdf');
    expect(utf8.decode(receipt.bytes), startsWith('%PDF'));

    final path = await service.share(orderId: 42, orderLabel: 'KSG-2610-00042');
    expect(path, '/tmp/recu-42.pdf');
    expect(writtenName, 'recu-42.pdf');
    expect(utf8.decode(writtenBytes!), contains('%PDF'));
  });

  test('le partage transmet le numéro de commande et le nom du client', () async {
    final api = _FakeApi();
    String? sharedText;
    String? sharedSubject;
    String? sharedPath;

    final service = ReceiptService(
      api,
      writer: (name, content) async => '/tmp/$name',
      sharer: (path, text, subject) async {
        sharedPath = path;
        sharedText = text;
        sharedSubject = subject;
      },
    );

    await service.share(
      orderId: 7,
      orderLabel: 'KSG-2610-00007',
      customerName: 'Awa Diallo',
    );

    expect(sharedPath, '/tmp/recu-7.pdf');
    expect(sharedText, contains('KSG-2610-00007'));
    expect(sharedText, contains('Awa Diallo'));
    expect(sharedSubject, 'Reçu KSG-2610-00007');
  });

  test('une commande non encaissée ne produit aucun partage', () async {
    final api = _FakeApi(
      error: ApiException(
        'Aucun encaissement à justifier pour cette commande.',
        statusCode: 400,
      ),
    );
    var shared = false;
    final service = ReceiptService(
      api,
      writer: (name, content) async => '/tmp/$name',
      sharer: (path, text, subject) async => shared = true,
    );

    await expectLater(
      service.share(orderId: 3),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          contains('Aucun encaissement'),
        ),
      ),
    );
    expect(shared, isFalse);
  });
}

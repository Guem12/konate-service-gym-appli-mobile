import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../config.dart';

/// Erreur métier renvoyée par l'API (message déjà lisible par l'utilisateur).
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.code});

  final String message;
  final int? statusCode;
  /// Code métier optionnel renvoyé par l'API (`otp_required`, `locked`…).
  final String? code;

  bool get isUnauthorized => statusCode == 401;
  bool get requiresOtp => code == 'otp_required' || code == 'otp_invalid';

  @override
  String toString() => message;
}

/// Client HTTP centralisé : jeton JWT, rafraîchissement automatique, erreurs
/// normalisées en [ApiException].
class ApiClient {
  ApiClient({http.Client? httpClient, FlutterSecureStorage? storage})
      : _http = httpClient ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage();

  final http.Client _http;
  final FlutterSecureStorage _storage;

  static const _accessKey = 'ksg_access_token';
  static const _refreshKey = 'ksg_refresh_token';

  String? _accessToken;
  Future<bool>? _refreshing;

  Future<void> loadTokens() async {
    _accessToken = await _storage.read(key: _accessKey);
  }

  bool get hasToken => _accessToken != null && _accessToken!.isNotEmpty;

  Future<void> saveTokens({String? access, String? refresh}) async {
    if (access != null) {
      _accessToken = access;
      await _storage.write(key: _accessKey, value: access);
    }
    if (refresh != null) {
      await _storage.write(key: _refreshKey, value: refresh);
    }
  }

  Future<void> clearTokens() async {
    _accessToken = null;
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final base = Uri.parse(AppConfig.apiBaseUrl);
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    return base.replace(
      path: '${base.path}/$cleanPath',
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
    );
  }

  Map<String, String> _headers({bool json = true}) => {
        if (json) 'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (hasToken) 'Authorization': 'Bearer $_accessToken',
      };

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) =>
      _send(() => _http.get(_uri(path, query), headers: _headers()));

  Future<dynamic> post(String path, {Object? body}) => _send(
        () => _http.post(
          _uri(path),
          headers: _headers(),
          body: body == null ? null : jsonEncode(body),
        ),
      );

  Future<dynamic> patch(String path, {Object? body}) => _send(
        () => _http.patch(
          _uri(path),
          headers: _headers(),
          body: body == null ? null : jsonEncode(body),
        ),
      );

  Future<dynamic> delete(String path) =>
      _send(() => _http.delete(_uri(path), headers: _headers()));

  /// Télécharge un binaire protégé (facture, reçu PDF) avec le même jeton.
  Future<Uint8List> getBytes(String path, {Map<String, dynamic>? query}) async {
    Future<http.Response> run() =>
        _http.get(_uri(path, query), headers: _headers(json: false));

    var response = await run();
    if (response.statusCode == 401 && hasToken && await _refreshToken()) {
      response = await run();
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response.bodyBytes;
    }
    throw ApiException(
      _extractMessage(_tryJson(response)) ?? 'Erreur ${response.statusCode}',
      statusCode: response.statusCode,
    );
  }

  Map<String, dynamic>? _tryJson(http.Response response) {
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      return decoded is Map<String, dynamic> ? decoded : null;
    } on FormatException {
      return null;
    }
  }

  Future<dynamic> _send(Future<http.Response> Function() request) async {
    var response = await request().timeout(
      AppConfig.requestTimeout,
      onTimeout: () => throw ApiException(
        'La requête a expiré. Vérifiez votre connexion.',
        statusCode: 408,
      ),
    );
    debugPrint('>>> API ${response.request?.method} ${response.request?.url} => ${response.statusCode}');
    debugPrint('>>> API body: ${response.body}');
    if (response.statusCode == 401 && hasToken) {
      final refreshed = await _refreshToken();
      if (refreshed) {
        response = await request().timeout(
          AppConfig.requestTimeout,
          onTimeout: () => throw ApiException(
            'La requête a expiré. Vérifiez votre connexion.',
            statusCode: 408,
          ),
        );
        debugPrint('>>> API (after refresh) ${response.request?.method} ${response.request?.url} => ${response.statusCode}');
        debugPrint('>>> API body: ${response.body}');
      }
    }
    return _decode(response);
  }

  /// Le serveur n'accepte qu'un seul rafraîchissement à la fois : on mutualise.
  Future<bool> _refreshToken() {
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<bool> _doRefresh() async {
    final refresh = await _storage.read(key: _refreshKey);
    if (refresh == null || refresh.isEmpty) return false;
    try {
      final response = await _http.post(
        _uri('auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh': refresh}),
      );
      if (response.statusCode != 200) return false;
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await saveTokens(
        access: data['access'] as String?,
        refresh: data['refresh'] as String?,
      );
      return true;
    } on Exception {
      return false;
    }
  }

  dynamic _decode(http.Response response) {
    final isJson = (response.headers['content-type'] ?? '').contains('json');
    dynamic body;
    if (isJson && response.body.isNotEmpty) {
      try {
        body = jsonDecode(utf8.decode(response.bodyBytes));
      } on FormatException {
        body = null;
      }
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }
    throw ApiException(
      _extractMessage(body) ?? 'Erreur ${response.statusCode}',
      statusCode: response.statusCode,
      code: body is Map ? body['code'] as String? : null,
    );
  }

  String? _extractMessage(dynamic body) {
    if (body is String) return body;
    if (body is! Map) return null;
    final detail = body['detail'] ?? body['error'] ?? body['non_field_errors'];
    if (detail is String) return detail;
    if (detail is List && detail.isNotEmpty) return '${detail.first}';
    // Erreurs de validation par champ : on affiche la première.
    for (final entry in body.entries) {
      final value = entry.value;
      if (value is List && value.isNotEmpty) return '${value.first}';
      if (value is String && value.isNotEmpty) return value;
    }
    return null;
  }
}

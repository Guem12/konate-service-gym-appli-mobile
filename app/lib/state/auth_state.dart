import 'package:flutter/foundation.dart';

import '../api/api_client.dart';
import '../models/models.dart';

/// Source de vérité de la session : jeton, profil, rôle et déconnexion.
class AuthState extends ChangeNotifier {
  AuthState(this.api);

  final ApiClient api;

  User? user;
  bool initializing = true;
  bool busy = false;

  bool get isLoggedIn => user != null;
  bool get isStaff => user?.isStaff ?? false;

  /// Recharge la session au démarrage de l'application.
  Future<void> bootstrap() async {
    try {
      await api.loadTokens();
      if (api.hasToken) {
        await refreshProfile();
      }
    } on ApiException {
      await api.clearTokens();
      user = null;
    } finally {
      initializing = false;
      notifyListeners();
    }
  }

  Future<void> login({
    required String phone,
    required String password,
    String otpCode = '',
  }) async {
    busy = true;
    notifyListeners();
    try {
      final payload = {
        'phone': phone,
        'password': password,
        if (otpCode.isNotEmpty) 'otp_code': otpCode,
      };
      debugPrint('>>> LOGIN payload: $payload');
      final data = await api.post('/auth/login', body: payload)
          as Map<String, dynamic>;
      debugPrint('>>> LOGIN response: $data');
      final tokens = Map<String, dynamic>.from(data['tokens'] as Map);
      await api.saveTokens(
        access: tokens['access'] as String?,
        refresh: tokens['refresh'] as String?,
      );
      user = User.fromJson(Map<String, dynamic>.from(data['user'] as Map));
    } catch (e, st) {
      debugPrint('>>> LOGIN ERROR: $e');
      debugPrint('>>> LOGIN STACK: $st');
      rethrow;
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> register({
    required String fullName,
    required String phone,
    required String password,
  }) async {
    busy = true;
    notifyListeners();
    try {
      final cleanPhone = phone.startsWith('223') ? phone.substring(3) : phone;
      final payload = {
        'full_name': fullName,
        'phone': cleanPhone,
        'password': password,
      };
      debugPrint('>>> REGISTER payload: $payload');
      final data = await api.post('/auth/register', body: payload)
          as Map<String, dynamic>;
      debugPrint('>>> REGISTER response: $data');
      final tokens = Map<String, dynamic>.from(data['tokens'] as Map);
      await api.saveTokens(
        access: tokens['access'] as String?,
        refresh: tokens['refresh'] as String?,
      );
      user = User.fromJson(Map<String, dynamic>.from(data['user'] as Map));
    } catch (e, st) {
      debugPrint('>>> REGISTER ERROR: $e');
      debugPrint('>>> REGISTER STACK: $st');
      rethrow;
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> refreshProfile() async {
    final data = await api.get('/auth/me');
    if (data is Map<String, dynamic>) {
      user = User.fromJson(data);
      notifyListeners();
    }
  }

  Future<void> updateProfile({String? fullName, String? email, String? photoBase64}) async {
    final body = <String, dynamic>{
      'full_name': ?fullName,
      'email': ?email,
      'photo_base64': ?photoBase64,
    };
    final data = await api.patch('/auth/me', body: body);
    if (data is Map<String, dynamic>) {
      user = User.fromJson(data);
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await api.clearTokens();
    user = null;
    notifyListeners();
  }
}

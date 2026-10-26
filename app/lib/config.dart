import 'package:flutter/foundation.dart';

/// Configuration de l'application.
///
/// L'URL de l'API se change sans toucher au code :
///   flutter run --dart-define=API_BASE_URL=https://api.exemple.ml/api/v1
///
/// Par défaut :
///   - Web (navigateur Edge/Chrome) : http://127.0.0.1:8000/api/v1
///   - Émulateur Android : http://10.0.2.2:8000/api/v1
class AppConfig {
  static String get apiBaseUrl {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) return fromEnv;
    if (kIsWeb) return 'http://127.0.0.1:8000/api/v1';
    return 'http://10.0.2.2:8000/api/v1';
  }

  /// Durée de validité indicative du jeton d'accès (le serveur reste maître).
  static const Duration requestTimeout = Duration(seconds: 20);
}

/// Coordonnées de la boutique, utilisées quand l'API n'est pas joignable.
class ShopDefaults {
  static const String name = 'Konaté-Service-Gym';
  static const String whatsapp = '22382445807';
  static const String city = 'Bamako';
}

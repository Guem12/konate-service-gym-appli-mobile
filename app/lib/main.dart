import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'api/repository.dart';
import 'core/theme.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'services/receipt_service.dart';
import 'state/auth_state.dart';
import 'state/cart_state.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await initializeDateFormatting('fr_FR');
  Intl.defaultLocale = 'fr_FR';
  runApp(const KsgApp());
}

class KsgApp extends StatefulWidget {
  const KsgApp({super.key});

  @override
  State<KsgApp> createState() => _KsgAppState();
}

class _KsgAppState extends State<KsgApp> {
  late final ApiClient _api = ApiClient();
  late final AuthState _auth = AuthState(_api);
  late final CartState _cart = CartState(_api);
  late final Repository _repository = Repository(_api);

  @override
  void initState() {
    super.initState();
    _auth.bootstrap();
    _setupPushNotifications();
  }

  Future<void> _setupPushNotifications() async {
    // Request permission for iOS
    if (kIsWeb || defaultTargetPlatform == TargetPlatform.android) {
      await _messaging.requestPermission();
    }

    // Get the initial message (notification opened from quit/background state)
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      // Handle the notification data
      final notification = initialMessage.data;
      debugPrint('>>> Initial notification: $notification');
    }

    // Listen for incoming messages while app is in foreground
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debug.print('>>> Foreground message: ${message.notification?.title}');
    });

    // Listen for messages when app is in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debug.print('>>> Background message opened app: ${message.notification?.title}');
    });

    // Get the token for sending notifications
    final token = await _messaging.getToken();
    debugPrint('>>> FCM Token: $token');
  }

  @override
  void dispose() {
    _auth.dispose();
    _cart.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<Repository>.value(value: _repository),
        Provider<ReceiptService>(create: (_) => ReceiptService(_api)),
        ChangeNotifierProvider<AuthState>.value(value: _auth),
        ChangeNotifierProvider<CartState>.value(value: _cart),
      ],
      child: MaterialApp(
        title: 'Konaté-Service-Gym',
        debugShowCheckedModeBanner: false,
        theme: buildTheme(),
        locale: const Locale('fr', 'FR'),
        home: const _RootGate(),
      ),
    );
  }
}

/// Aiguillage : splash → onboarding → connexion → application selon la session.
class _RootGate extends StatelessWidget {
  const _RootGate();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthState>();
    if (auth.initializing) {
      return const _SplashScreen();
    }

    // Si connecté, on affiche directement l'application complète
    if (auth.isLoggedIn) {
      return const MainShell();
    }

    // Sinon, connexion directe
    return const LoginScreen();
  }
}

/// Splash screen brandé Konaté Service Gym
class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Color(0xFF0D1B2A),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Cercle avec KS
            _KsCircle(),
            SizedBox(height: 28),
            Text(
              'Konaté Service Gym',
              style: TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.4,
              ),
            ),
            SizedBox(height: 6),
            Text(
              'Matériel de gym • Bamako',
              style: TextStyle(
                color: Color(0xFF5A6A7A),
                fontSize: 13,
              ),
            ),
            SizedBox(height: 48),
            SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: Color(0xFF2DC97E),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _KsCircle extends StatelessWidget {
  const _KsCircle();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 110,
      height: 110,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: const Color(0xFF162435),
        border: Border.all(color: const Color(0xFF2DC97E), width: 3),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF2DC97E).withValues(alpha: 0.3),
            blurRadius: 30,
            spreadRadius: 4,
          ),
        ],
      ),
      child: Center(
        child: RichText(
          text: const TextSpan(
            children: [
              TextSpan(
                text: 'K',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 38,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -2,
                ),
              ),
              TextSpan(
                text: 'S',
                style: TextStyle(
                  color: Color(0xFF2DC97E),
                  fontSize: 38,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
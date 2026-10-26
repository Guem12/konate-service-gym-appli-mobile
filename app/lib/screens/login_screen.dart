import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../core/format.dart';
import '../core/theme.dart';
import '../state/auth_state.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _otp = TextEditingController();
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  bool _obscure = true;
  bool _otpRequired = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..forward();
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
  }

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    _otp.dispose();
    _fadeCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _error = null);
    final auth = context.read<AuthState>();
    try {
      await auth.login(
        phone: normalizePhoneInput(_phone.text),
        password: _password.text,
        otpCode: _otp.text.trim(),
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _otpRequired = e.requiresOtp;
        _error = e.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthState>();
    final size = MediaQuery.sizeOf(context);

    return Scaffold(
      backgroundColor: KsgColors.navy,
      body: Stack(
        children: [
          // Cercles décoratifs en arrière-plan (inspirés du logo circulaire)
          Positioned(
            top: -size.height * 0.12,
            right: -size.width * 0.25,
            child: _glowCircle(size.width * 0.75),
          ),
          Positioned(
            bottom: -size.height * 0.06,
            left: -size.width * 0.2,
            child: _glowCircle(size.width * 0.55),
          ),

          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 28, vertical: 32),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: FadeTransition(
                    opacity: _fadeAnim,
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // ─── Logo ───────────────────────────────────────
                          Center(
                            child: Container(
                              width: 100,
                              height: 100,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: KsgColors.green,
                                  width: 3,
                                ),
                                color: KsgColors.navyCard,
                                boxShadow: [
                                  BoxShadow(
                                    color: KsgColors.green.withValues(alpha: 0.35),
                                    blurRadius: 28,
                                    spreadRadius: 2,
                                  ),
                                ],
                              ),
                              child: const Center(
                                child: _KsLogo(),
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // ─── Titre ──────────────────────────────────────
                          const Text(
                            'Konaté Service Gym',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.w800,
                              color: Colors.white,
                              letterSpacing: -0.5,
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Matériel de gym à Bamako',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: KsgColors.muted,
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(height: 36),

                          // ─── Card formulaire ────────────────────────────
                          Container(
                            padding: const EdgeInsets.all(24),
                            decoration: BoxDecoration(
                              color: KsgColors.navyCard,
                              borderRadius: BorderRadius.circular(24),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.07),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                const Text(
                                  'Connexion',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 18,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 20),

                                // Téléphone
                                _darkField(
                                  controller: _phone,
                                  label: 'Numéro de téléphone',
                                  hint: '70 00 00 00',
                                  icon: Icons.phone_iphone_rounded,
                                  keyboardType: TextInputType.phone,
                                  validator: (value) {
                                    final normalized =
                                        normalizePhoneInput(value ?? '');
                                    if (normalized.length != 11) {
                                      return 'Entrez 8 chiffres (ex. 70 00 00 00).';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 14),

                                // Mot de passe
                                _darkField(
                                  controller: _password,
                                  label: 'Mot de passe',
                                  icon: Icons.lock_outline_rounded,
                                  obscureText: _obscure,
                                  suffixIcon: IconButton(
                                    icon: Icon(
                                      _obscure
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                      color: KsgColors.muted,
                                    ),
                                    onPressed: () =>
                                        setState(() => _obscure = !_obscure),
                                  ),
                                  validator: (value) =>
                                      (value == null || value.isEmpty)
                                          ? 'Saisissez votre mot de passe.'
                                          : null,
                                ),

                                // OTP (si requis)
                                if (_otpRequired) ...[
                                  const SizedBox(height: 14),
                                  _darkField(
                                    controller: _otp,
                                    label: 'Code de double authentification',
                                    icon: Icons.verified_user_outlined,
                                    keyboardType: TextInputType.number,
                                  ),
                                ],

                                // Message d'erreur
                                if (_error != null) ...[
                                  const SizedBox(height: 14),
                                  Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: KsgColors.red.withValues(alpha: 0.15),
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(
                                        color: KsgColors.red.withValues(alpha: 0.4),
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        const Icon(Icons.error_outline,
                                            color: KsgColors.red, size: 18),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            _error!,
                                            style: const TextStyle(
                                                color: KsgColors.red,
                                                fontSize: 13),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],

                                const SizedBox(height: 24),

                                // Bouton connexion
                                SizedBox(
                                  height: 54,
                                  child: FilledButton(
                                    onPressed: auth.busy ? null : _submit,
                                    style: FilledButton.styleFrom(
                                      backgroundColor: KsgColors.green,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(16),
                                      ),
                                    ),
                                    child: auth.busy
                                        ? const SizedBox(
                                            height: 20,
                                            width: 20,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Colors.white,
                                            ),
                                          )
                                        : const Text(
                                            'Se connecter',
                                            style: TextStyle(
                                              fontSize: 16,
                                              fontWeight: FontWeight.w700,
                                            ),
                                          ),
                                  ),
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: 20),

                          // Créer un compte
                          OutlinedButton(
                            onPressed: auth.busy
                                ? null
                                : () => Navigator.of(context).push(
                                      MaterialPageRoute(
                                          builder: (_) =>
                                              const RegisterScreen()),
                                    ),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.white,
                              side: BorderSide(
                                color: Colors.white.withValues(alpha: 0.25),
                              ),
                              minimumSize: const Size.fromHeight(50),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                              ),
                            ),
                            child: const Text('Créer un compte client'),
                          ),

                          const SizedBox(height: 24),
                          const Text(
                            'Besoin d\'aide ? Contactez-nous sur WhatsApp.',
                            textAlign: TextAlign.center,
                            style:
                                TextStyle(fontSize: 12, color: KsgColors.muted),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Cercle décoratif lumineux (fond)
  Widget _glowCircle(double size) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: KsgColors.green.withValues(alpha: 0.12),
          width: 1.5,
        ),
        gradient: RadialGradient(
          colors: [
            KsgColors.green.withValues(alpha: 0.08),
            Colors.transparent,
          ],
        ),
      ),
    );
  }

  /// Champ texte style dark
  Widget _darkField({
    required TextEditingController controller,
    required String label,
    String? hint,
    required IconData icon,
    TextInputType? keyboardType,
    bool obscureText = false,
    Widget? suffixIcon,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscureText,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        labelStyle: const TextStyle(color: KsgColors.muted),
        hintStyle: const TextStyle(color: KsgColors.muted),
        prefixIcon: Icon(icon, color: KsgColors.green, size: 20),
        suffixIcon: suffixIcon,
        filled: true,
        fillColor: KsgColors.navy.withValues(alpha: 0.6),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide:
              BorderSide(color: Colors.white.withValues(alpha: 0.1)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide:
              BorderSide(color: Colors.white.withValues(alpha: 0.1)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: KsgColors.green, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: KsgColors.red.withValues(alpha: 0.7)),
        ),
      ),
      validator: validator,
    );
  }
}

/// Monogramme « KS » stylisé (logo simplifié dans l'app)
class _KsLogo extends StatelessWidget {
  const _KsLogo();

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: const TextSpan(
        children: [
          TextSpan(
            text: 'K',
            style: TextStyle(
              color: Colors.white,
              fontSize: 32,
              fontWeight: FontWeight.w900,
              letterSpacing: -2,
            ),
          ),
          TextSpan(
            text: 'S',
            style: TextStyle(
              color: KsgColors.green,
              fontSize: 32,
              fontWeight: FontWeight.w900,
              letterSpacing: -2,
            ),
          ),
        ],
      ),
    );
  }
}

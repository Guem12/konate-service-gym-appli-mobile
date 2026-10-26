import 'package:flutter/material.dart';

abstract final class KsgColors {
  // PRIMARY BRAND COLORS (from original logo)
  static const navy = Color(0xFF0D1B2A);
  static const navyLight = Color(0xFF162435);
  static const navyCard = Color(0xFF1E2F42);
  static const green = Color(0xFF2DC97E);
  static const greenDark = Color(0xFF1FA862);
  static const greenAccent = Color(0xFF10e083);
  static const gold = Color(0xFFF2B807);
  static const greenGlow = Color(0x332DC97E);
  static const red = Color(0xFFFF4D4D);
  static const ink = Color(0xFF0D1B2A);

  // LOGO WIDGET
  static Widget logoMonogram(double size) => KsgLogoMonogram(size: size);

  // SURFACES
  static const sand = Color(0xFFF4F6F9);
  static const surface = Color(0xFFFFFFFF);

  // TEXT COLORS
  static const textPrimary = Color(0xFF0D1B2A);
  static const textSecondary = Color(0xFF5A6A7A);
  static const muted = Color(0xFF8A9AAA);

  // LOGO & BRAND ACCENTS
  static const logoNavy = Color(0xFF101c24);
  static const logoWhite = Color(0xFFFFFFFF);
  static const logoGreen = Color(0xFF10e083);
  static const logoNavyCard = Color(0xFF16283a);

  // ETATS ET INTERACTIONS
  static const buttonDisabled = Color(0xFFE2E5E8);
}

/// Monogram widget displaying the KS Konaté Service Gym logo
class KsgLogoMonogram extends StatelessWidget {
  final double size;

  const KsgLogoMonogram({
    required this.size,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
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

ThemeData buildTheme() {
  final colorScheme = ColorScheme(
    brightness: Brightness.light,
    primary: KsgColors.green,
    onPrimary: Colors.white,
    secondary: KsgColors.gold,
    onSecondary: KsgColors.navy,
    surface: KsgColors.surface,
    onSurface: KsgColors.navy,
    error: KsgColors.red,
    onError: Colors.white,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: KsgColors.sand,

    appBarTheme: const AppBarTheme(
      backgroundColor: KsgColors.navy,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: false,
      scrolledUnderElevation: 0,
      titleTextStyle: TextStyle(
        color: Colors.white,
        fontSize: 20,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.3,
      ),
    ),

    cardTheme: CardThemeData(
      elevation: 0,
      color: KsgColors.surface,
      margin: const EdgeInsets.all(16),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
    ),

    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: KsgColors.green,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        textStyle: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
        elevation: 0,
        side: const BorderSide(color: KsgColors.greenAccent, width: 2),
      ),
    ),

    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: KsgColors.green,
        side: const BorderSide(color: KsgColors.greenAccent, width: 2),
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        textStyle: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),

    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: KsgColors.green,
        textStyle: const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: KsgColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFFD6D8DB), width: 1),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFFD6D8DB), width: 1),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: KsgColors.green, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: KsgColors.red, width: 1.5),
      ),
      labelStyle: const TextStyle(color: KsgColors.textSecondary),
      hintStyle: const TextStyle(color: KsgColors.muted),
      prefixIconColor: KsgColors.muted,
    ),

    chipTheme: ChipThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
      side: BorderSide.none,
      backgroundColor: KsgColors.green.withValues(alpha: 0.1),
      selectedColor: KsgColors.green,
      labelStyle: const TextStyle(
        fontWeight: FontWeight.w600,
        fontSize: 13,
        color: KsgColors.navy,
      ),
      secondarySelectedColor: KsgColors.greenAccent,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    ),

    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: KsgColors.surface,
      elevation: 0,
      height: 68,
      indicatorColor: KsgColors.green.withValues(alpha: 0.1),
      iconTheme: const WidgetStatePropertyAll(
        IconThemeData(color: KsgColors.muted, size: 24),
      ),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const TextStyle(
            fontSize: 11.5,
            fontWeight: FontWeight.w700,
            color: KsgColors.green,
          );
        }
        return const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          color: KsgColors.muted,
        );
      }),
    ),

    dividerTheme: const DividerThemeData(
      color: Color(0xFFEEF1F5),
      thickness: 1,
      space: 1,
    ),

    tabBarTheme: const TabBarThemeData(
      indicator: BoxDecoration(
        border: Border(bottom: BorderSide(color: KsgColors.green, width: 2)),
      ),
      labelColor: KsgColors.green,
      unselectedLabelColor: KsgColors.muted,
    ),
  );
}
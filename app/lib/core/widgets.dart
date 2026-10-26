import 'package:flutter/material.dart';

import '../models/models.dart';
import 'format.dart';
import 'theme.dart';

// ─────────────────────────────────────────────────────────────────────────────
// ProductThumb
// ─────────────────────────────────────────────────────────────────────────────

/// Image d'un produit avec placeholder fitness
class ProductThumb extends StatelessWidget {
  const ProductThumb({
    super.key,
    this.url,
    this.size = 88,
    this.radius = 14,
    this.iconSize = 32,
  });

  final String? url;
  final double size;
  final double radius;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    final clean = url?.trim();
    Widget content;

    if (clean == null || clean.isEmpty) {
      content = Center(
        child: Icon(
          Icons.fitness_center_rounded,
          color: KsgColors.muted,
          size: iconSize,
        ),
      );
    } else if (clean.startsWith('assets/')) {
      content = Image.asset(
        clean,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => Center(
          child: Icon(
            Icons.fitness_center_rounded,
            color: KsgColors.muted,
            size: iconSize,
          ),
        ),
      );
    } else {
      content = Image.network(
        clean,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => Center(
          child: Icon(
            Icons.fitness_center_rounded,
            color: KsgColors.muted,
            size: iconSize,
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: Container(
        width: size,
        height: size,
        color: const Color(0xFFEDF0F4),
        child: content,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// PriceTag
// ─────────────────────────────────────────────────────────────────────────────

class PriceTag extends StatelessWidget {
  const PriceTag({super.key, required this.product, this.fontSize = 15});

  final Product product;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 6,
      children: [
        Text(
          money(product.price),
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: FontWeight.w800,
            color: KsgColors.green,
          ),
        ),
        if (product.hasPromotion)
          Text(
            money(product.comparePrice!),
            style: TextStyle(
              fontSize: fontSize - 2,
              color: KsgColors.muted,
              decoration: TextDecoration.lineThrough,
            ),
          ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ProductCard (redesign premium)
// ─────────────────────────────────────────────────────────────────────────────

class ProductCard extends StatelessWidget {
  const ProductCard({
    super.key,
    required this.product,
    required this.onTap,
    this.onAdd,
  });

  final Product product;
  final VoidCallback onTap;
  final VoidCallback? onAdd;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: KsgColors.surface,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: KsgColors.navy.withValues(alpha: 0.07),
              blurRadius: 16,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ─── Image ───────────────────────────────────────────────────
            Stack(
              children: [
                AspectRatio(
                  aspectRatio: 1.2,
                  child: ProductThumb(
                    url: product.imageUrl,
                    size: double.infinity,
                    radius: 20,
                    iconSize: 40,
                  ),
                ),
                // Badge promo
                if (product.hasPromotion)
                  Positioned(
                    top: 10,
                    left: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 9, vertical: 4),
                      decoration: BoxDecoration(
                        color: KsgColors.gold,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text(
                        'PROMO',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w900,
                          color: Colors.black,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ),
                // Overlay rupture de stock
                if (!product.inStock)
                  Positioned.fill(
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      alignment: Alignment.center,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: 0.7),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Text(
                          'Rupture de stock',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),

            // ─── Info ─────────────────────────────────────────────────────
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 8, 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      product.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                        color: KsgColors.textPrimary,
                        height: 1.3,
                      ),
                    ),
                    Row(
                      children: [
                        Expanded(child: PriceTag(product: product)),
                        if (onAdd != null && product.inStock)
                          GestureDetector(
                            onTap: onAdd,
                            child: Container(
                              width: 34,
                              height: 34,
                              decoration: BoxDecoration(
                                color: KsgColors.green,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Icon(
                                Icons.add_rounded,
                                color: Colors.white,
                                size: 20,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// SectionHeader
// ─────────────────────────────────────────────────────────────────────────────

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    this.action,
    this.onAction,
  });

  final String title;
  final String? action;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 24, 12, 12),
      child: Row(
        children: [
          // Trait vert à gauche du titre
          Container(
            width: 4,
            height: 20,
            decoration: BoxDecoration(
              color: KsgColors.green,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: KsgColors.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
          ),
          if (action != null)
            GestureDetector(
              onTap: onAction,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: KsgColors.greenGlow,
                  borderRadius: BorderRadius.circular(100),
                ),
                child: Text(
                  action!,
                  style: const TextStyle(
                    color: KsgColors.green,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// StatusChip
// ─────────────────────────────────────────────────────────────────────────────

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.label, required this.status});

  final String label;
  final String status;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (status) {
      'delivered' => (const Color(0xFFE3F8EE), KsgColors.greenDark),
      'cancelled' || 'returned' => (const Color(0xFFFFEDED), KsgColors.red),
      'pending_payment' => (const Color(0xFFFFF4D6), const Color(0xFF8A6100)),
      'shipping' => (const Color(0xFFE4EEFB), const Color(0xFF12457F)),
      _ => (const Color(0xFFEDF0F4), KsgColors.textSecondary),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(100),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: fg,
          fontSize: 12,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// EmptyState
// ─────────────────────────────────────────────────────────────────────────────

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(36),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: KsgColors.greenGlow,
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(icon, size: 40, color: KsgColors.green),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: KsgColors.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            if (message != null) ...[
              const SizedBox(height: 8),
              Text(
                message!,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: KsgColors.textSecondary,
                  height: 1.5,
                ),
              ),
            ],
            if (action != null) ...[const SizedBox(height: 22), action!],
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ErrorView
// ─────────────────────────────────────────────────────────────────────────────

class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return EmptyState(
      icon: Icons.cloud_off_rounded,
      title: 'Connexion impossible',
      message: message,
      action: onRetry == null
          ? null
          : FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Réessayer'),
            ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// showMessage
// ─────────────────────────────────────────────────────────────────────────────

void showMessage(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
      ),
    );
}

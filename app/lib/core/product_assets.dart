/// Mapping des photos réelles des équipements du magasin Konaté-Service-Gym
/// stockées dans `assets/images/`.
class ProductAssets {
  static const Map<String, List<String>> _slugToImages = {
    // 1. Haltères
    'halteres-hexagonaux': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.02.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.02 (1).jpeg',
    ],
    // 2. Disques olympiques
    'disques-olympiques': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.19 (1).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.19 (2).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.19 (3).jpeg',
    ],
    // 3. Barre olympique 2 m
    'barre-olympique-2-m': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.03.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.02 (1).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.19 (3).jpeg',
    ],
    // 4. Banc de musculation inclinable
    'banc-de-musculation-inclinable': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.22 (1).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.22 (2).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.22 (3).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.22.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.21 (2).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.21 (3).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.06.jpeg',
    ],
    // 5. Rack squat
    'rack-squat': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.01.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.05 (1).jpeg',
    ],
    // 6. Banc romain / Six Pack Care
    'banc-romain': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.17.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.17 (1).jpeg',
    ],
    // 7. Presse à cuisses / Multi-gym G-STAR
    'presse-a-cuisses': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.21.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.21 (1).jpeg',
    ],
    // 8. Machine poulie haute / Lat Pulldown
    'machine-poulie-haute': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.18 (3).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.21 (1).jpeg',
    ],
    // 9. Smith machine
    'smith-machine': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.19.jpeg',
    ],
    // 10. Tapis de course
    'tapis-de-course': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.00.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.02.59.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.08 (2).jpeg',
    ],
    // 11. Vélo d'appui / Spinning
    'velo-dappui': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.20.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.05.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.20 (4).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.20 (2).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.02.59 (1).jpeg',
    ],
    // 12. Rameur / Salle cardio
    'rameur': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.02.57.jpeg',
    ],
    // 13. Kettlebell / Plateforme vibrante
    'kettlebell': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.04 (1).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.04.jpeg',
    ],
    // 14. Corde à sauter / Sac de frappe
    'corde-a-sauter': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.17 (3).jpeg',
    ],
    // 15. Ceinture de force / Pèse-personne impédancemètre
    'ceinture-de-force': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.10.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.08 (3).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.09.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.11.jpeg',
    ],
    // 16. Tapis de sol fitness
    'tapis-de-sol-fitness': [
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.08.jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.06 (2).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.06 (1).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.08 (1).jpeg',
      'assets/images/WhatsApp Image 2026-10-16 at 15.03.20 (1).jpeg',
    ],
  };

  /// Mapping de secours par ID de produit
  static const Map<int, String> _idToPrimary = {
    1: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.02.jpeg',
    2: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.19 (1).jpeg',
    3: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.03.jpeg',
    4: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.22 (1).jpeg',
    5: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.01.jpeg',
    6: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.17.jpeg',
    7: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.21.jpeg',
    8: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.18 (3).jpeg',
    9: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.19.jpeg',
    10: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.00.jpeg',
    11: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.20.jpeg',
    12: 'assets/images/WhatsApp Image 2026-10-16 at 15.02.57.jpeg',
    13: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.04 (1).jpeg',
    14: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.17 (3).jpeg',
    15: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.10.jpeg',
    16: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.08.jpeg',
  };

  /// Retourne l'image principale pour un équipement donné
  static String? getPrimaryImage({String? slug, int? id, String? name}) {
    if (slug != null && _slugToImages.containsKey(slug)) {
      return _slugToImages[slug]!.first;
    }
    if (id != null && _idToPrimary.containsKey(id)) {
      return _idToPrimary[id];
    }
    if (name != null) {
      final lower = name.toLowerCase();
      for (final entry in _slugToImages.entries) {
        final keyWords = entry.key.split('-');
        if (keyWords.any((kw) => kw.length > 3 && lower.contains(kw))) {
          return entry.value.first;
        }
      }
    }
    return null;
  }

  /// Retourne la galerie complète de photos réelles pour un équipement
  static List<String> getGallery({String? slug, int? id, String? name}) {
    if (slug != null && _slugToImages.containsKey(slug)) {
      return _slugToImages[slug]!;
    }
    if (id != null && _idToPrimary.containsKey(id)) {
      final primary = _idToPrimary[id]!;
      for (final list in _slugToImages.values) {
        if (list.contains(primary)) return list;
      }
      return [primary];
    }
    return const [];
  }
}

/// Mapping des photos réelles pour les catégories
class CategoryAssets {
  static const Map<String, String> _slugToImage = {
    'musculation': 'assets/images/WhatsApp Image 2026-10-16 at 15.03.19 (1).jpeg',
    'bancs-et-supports': 'assets/images/WhatsApp Image 2026-10-16 at 15.03.22 (1).jpeg',
    'machines': 'assets/images/WhatsApp Image 2026-10-16 at 15.03.21.jpeg',
    'cardio': 'assets/images/WhatsApp Image 2026-10-16 at 15.03.00.jpeg',
    'accessoires': 'assets/images/WhatsApp Image 2026-10-16 at 15.03.08.jpeg',
  };

  static const Map<int, String> _idToImage = {
    1: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.19 (1).jpeg',
    2: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.22 (1).jpeg',
    3: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.21.jpeg',
    4: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.00.jpeg',
    5: 'assets/images/WhatsApp Image 2026-10-16 at 15.03.08.jpeg',
  };

  static String? getImage({String? slug, int? id, String? name}) {
    if (slug != null && _slugToImage.containsKey(slug)) {
      return _slugToImage[slug];
    }
    if (id != null && _idToImage.containsKey(id)) {
      return _idToImage[id];
    }
    if (name != null) {
      final lower = name.toLowerCase();
      if (lower.contains('muscu')) return _slugToImage['musculation'];
      if (lower.contains('banc') || lower.contains('support')) return _slugToImage['bancs-et-supports'];
      if (lower.contains('machine')) return _slugToImage['machines'];
      if (lower.contains('cardio')) return _slugToImage['cardio'];
      if (lower.contains('access')) return _slugToImage['accessoires'];
    }
    return null;
  }
}

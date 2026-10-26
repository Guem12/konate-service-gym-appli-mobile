import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/api_client.dart';
import '../api/repository.dart';
import '../core/format.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import '../state/auth_state.dart';
import '../state/cart_state.dart';
import 'admin/admin_deliveries.dart';
import 'admin/admin_home.dart';
import 'admin/admin_orders.dart';
import 'admin/admin_payments.dart';
import 'admin/admin_products.dart';
import 'orders_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _isUploadingPhoto = false;

  Future<void> _pickAndUploadPhoto() async {
    final auth = context.read<AuthState>();
    final user = auth.user;
    if (user == null) return;

    final picker = ImagePicker();
    final action = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 4, 20, 12),
                child: Text(
                  'Photo de profil',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                ),
              ),
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: KsgColors.greenGlow,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.photo_camera_rounded, color: KsgColors.green),
                ),
                title: const Text('Prendre une photo'),
                subtitle: const Text('Ouvrir l\'appareil photo'),
                onTap: () => Navigator.pop(context, 'camera'),
              ),
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.photo_library_rounded, color: Color(0xFF3B82F6)),
                ),
                title: const Text('Choisir depuis la galerie'),
                subtitle: const Text('Sélectionner une photo de votre appareil'),
                onTap: () => Navigator.pop(context, 'gallery'),
              ),
              if (user.photoUrl != null && user.photoUrl!.isNotEmpty)
                ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF2F2),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.delete_outline_rounded, color: KsgColors.red),
                  ),
                  title: const Text(
                    'Supprimer la photo',
                    style: TextStyle(color: KsgColors.red, fontWeight: FontWeight.w600),
                  ),
                  onTap: () => Navigator.pop(context, 'delete'),
                ),
            ],
          ),
        ),
      ),
    );

    if (action == null || !mounted) return;

    if (action == 'delete') {
      setState(() => _isUploadingPhoto = true);
      try {
        await auth.updateProfile(photoBase64: 'DELETE');
        if (mounted) showMessage(context, 'Photo de profil supprimée.');
      } on ApiException catch (e) {
        if (mounted) showMessage(context, e.message);
      } finally {
        if (mounted) setState(() => _isUploadingPhoto = false);
      }
      return;
    }

    final ImageSource source =
        action == 'camera' ? ImageSource.camera : ImageSource.gallery;

    try {
      final XFile? file = await picker.pickImage(
        source: source,
        maxWidth: 800,
        maxHeight: 800,
        imageQuality: 85,
      );
      if (file == null || !mounted) return;

      setState(() => _isUploadingPhoto = true);
      final bytes = await file.readAsBytes();
      final base64String = 'data:image/jpeg;base64,${base64Encode(bytes)}';

      await auth.updateProfile(photoBase64: base64String);
      if (mounted) {
        showMessage(context, 'Photo de profil mise à jour avec succès !');
      }
    } catch (e) {
      if (mounted) {
        showMessage(context, 'Impossible de charger la photo sélectionnée.');
      }
    } finally {
      if (mounted) setState(() => _isUploadingPhoto = false);
    }
  }

  Future<void> _editName() async {
    final auth = context.read<AuthState>();
    final controller = TextEditingController(text: auth.user?.fullName ?? '');
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Modifier mon nom'),
        content: TextField(
          controller: controller,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(labelText: 'Nom complet'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Annuler')),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Enregistrer'),
          ),
        ],
      ),
    );
    if (name == null || name.length < 3 || !mounted) return;
    try {
      await auth.updateProfile(fullName: name);
      if (mounted) showMessage(context, 'Nom mis à jour avec succès.');
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  Future<void> _editEmail() async {
    final auth = context.read<AuthState>();
    final controller = TextEditingController(text: auth.user?.email ?? '');
    final email = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Modifier mon adresse e-mail'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(
            labelText: 'Adresse e-mail',
            hintText: 'exemple@gmail.com',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Annuler')),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Enregistrer'),
          ),
        ],
      ),
    );
    if (email == null || !mounted) return;
    try {
      await auth.updateProfile(email: email);
      if (mounted) showMessage(context, 'Adresse e-mail mise à jour.');
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  Future<void> _contactWhatsApp() async {
    final settings = await context.read<Repository>().settings();
    final uri = Uri.parse('https://wa.me/${settings.whatsappPhone}');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && mounted) {
      showMessage(context, 'WhatsApp indisponible.');
    }
  }

  Future<void> _deleteAccount() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Supprimer mon compte ?'),
        content: const Text(
          'Vos données personnelles seront anonymisées. Vos commandes passées restent '
          'conservées pour la comptabilité de la boutique.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: KsgColors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      await context.read<ApiClient>().delete('/auth/me/delete');
      if (!mounted) return;
      context.read<CartState>().reset();
      await context.read<AuthState>().logout();
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  Future<void> _logout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Se déconnecter ?'),
        content: const Text('Voulez-vous vraiment fermer votre session ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: KsgColors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Déconnexion'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    context.read<CartState>().reset();
    await context.read<AuthState>().logout();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthState>();
    final user = auth.user;
    if (user == null) return const SizedBox.shrink();

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(user.isStaff ? 'Profil Administrateur' : 'Mon profil'),
        backgroundColor: user.isStaff ? const Color(0xFF0F172A) : Colors.white,
        foregroundColor: user.isStaff ? Colors.white : const Color(0xFF0F172A),
        elevation: 0,
        actions: [
          if (user.isStaff)
            IconButton(
              icon: const Icon(Icons.dashboard_customize_outlined),
              tooltip: 'Accéder à la console Admin',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const AdminHomeScreen()),
              ),
            ),
        ],
      ),
      body: user.isStaff ? _buildAdminProfile(user) : _buildClientProfile(user),
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ── AVATAR AVEC BOUTON PHOTO (COMMUN AUX DEUX PROFILS) ────────────────────────
  // ─────────────────────────────────────────────────────────────────────────────

  Widget _buildAvatar(User user, {double radius = 38}) {
    final hasPhoto = user.photoUrl != null && user.photoUrl!.isNotEmpty;
    final initials = user.fullName.isNotEmpty
        ? user.fullName.trim().split(' ').map((e) => e.isNotEmpty ? e[0] : '').take(2).join().toUpperCase()
        : '?';

    return Stack(
      alignment: Alignment.center,
      children: [
        Container(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: user.isStaff ? const Color(0xFF10B981) : Colors.white,
              width: 3,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.15),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: CircleAvatar(
            radius: radius,
            backgroundColor: user.isStaff ? const Color(0xFF1E293B) : KsgColors.greenDark,
            backgroundImage: hasPhoto ? NetworkImage(user.photoUrl!) : null,
            child: _isUploadingPhoto
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                  )
                : (!hasPhoto
                    ? Text(
                        initials,
                        style: TextStyle(
                          fontSize: radius * 0.7,
                          fontWeight: FontWeight.w900,
                          color: user.isStaff ? const Color(0xFF34D399) : Colors.white,
                        ),
                      )
                    : null),
          ),
        ),
        Positioned(
          bottom: 0,
          right: 0,
          child: InkWell(
            onTap: _isUploadingPhoto ? null : _pickAndUploadPhoto,
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: user.isStaff ? const Color(0xFF10B981) : KsgColors.green,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 2),
                boxShadow: const [
                  BoxShadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2)),
                ],
              ),
              child: const Icon(
                Icons.camera_alt_rounded,
                size: 15,
                color: Colors.white,
              ),
            ),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ── PROFIL ADMINISTRATEUR (DESIGN EXÉCUTIF ET OUTILS DE GESTION) ─────────────
  // ─────────────────────────────────────────────────────────────────────────────

  Widget _buildAdminProfile(User user) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
      children: [
        // Carte d'identité administrateur
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: const Color(0xFF334155)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x33000000),
                blurRadius: 16,
                offset: Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            children: [
              Row(
                children: [
                  _buildAvatar(user, radius: 36),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: const Color(0xFF10B981).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: const Color(0xFF10B981)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.shield_rounded, size: 12, color: Color(0xFF34D399)),
                                  const SizedBox(width: 4),
                                  Text(
                                    user.roleLabel.toUpperCase(),
                                    style: const TextStyle(
                                      color: Color(0xFF34D399),
                                      fontSize: 10,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 0.6,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          user.fullName,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 19,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          prettyPhone(user.phone),
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
                        ),
                        if (user.email.isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            user.email,
                            style: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.lock_clock_rounded, size: 16, color: Color(0xFF10B981)),
                        SizedBox(width: 8),
                        Text(
                          'Session active · Console sécurisée',
                          style: TextStyle(color: Color(0xFFE2E8F0), fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                    TextButton(
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        minimumSize: const Size(50, 24),
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      onPressed: _pickAndUploadPhoto,
                      child: const Text('Changer photo', style: TextStyle(color: Color(0xFF34D399), fontSize: 12)),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 20),

        // Console d'Administration & Gestion
        _group('PILOTAGE DU COMMERCE', [
          _tile(
            Icons.dashboard_rounded,
            'Tableau de bord & Analytics',
            subtitle: 'Chiffre d\'affaires, marges & indicateurs clés',
            color: const Color(0xFF0F172A),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AdminHomeScreen()),
            ),
          ),
          _tile(
            Icons.inventory_2_rounded,
            'Gestion des stocks & catalogue',
            subtitle: 'Articles, alertes réapprovisionnement & prix',
            color: const Color(0xFF0D9488),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AdminProductsScreen()),
            ),
          ),
          _tile(
            Icons.point_of_sale_rounded,
            'Caisse & Point de Vente (POS)',
            subtitle: 'Enregistrement des ventes directes en boutique',
            color: const Color(0xFF16A34A),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AdminPaymentsScreen()),
            ),
          ),
          _tile(
            Icons.local_shipping_rounded,
            'Suivi des livraisons',
            subtitle: 'Courses en cours, chauffeurs & zones Bamako',
            color: const Color(0xFF2563EB),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AdminDeliveriesScreen()),
            ),
          ),
          _tile(
            Icons.people_alt_rounded,
            'Clients & Commandes boutique',
            subtitle: 'Base clients, commandes en ligne & statuts',
            color: const Color(0xFF7C3AED),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AdminOrdersScreen()),
            ),
          ),
        ]),

        const SizedBox(height: 16),

        // Sécurité du compte Admin
        _group('SÉCURITÉ ET ACCÈS PRIVILÉGIÉS', [
          _tile(
            user.twoFactorEnabled ? Icons.verified_user_rounded : Icons.gpp_maybe_rounded,
            'Double authentification (2FA)',
            subtitle: user.twoFactorEnabled
                ? 'Protection maximale activée via TOTP'
                : 'Recommandé pour protéger l\'accès administrateur',
            color: user.twoFactorEnabled ? const Color(0xFF16A34A) : const Color(0xFFEA580C),
            trailingWidget: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: user.twoFactorEnabled ? const Color(0xFFDCFCE7) : const Color(0xFFFFEDD5),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                user.twoFactorEnabled ? 'Active' : 'À configurer',
                style: TextStyle(
                  color: user.twoFactorEnabled ? const Color(0xFF15803D) : const Color(0xFFC2410C),
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            onTap: () => _twoFactor(user.twoFactorEnabled),
          ),
          _tile(
            Icons.key_rounded,
            'Changer le mot de passe administrateur',
            subtitle: 'Mettre à jour vos identifiants d\'accès',
            color: const Color(0xFF475569),
            onTap: _changePassword,
          ),
        ]),

        const SizedBox(height: 16),

        // Paramètres personnels Admin
        _group('COORDONNÉES PERSONNELLES', [
          _tile(
            Icons.badge_outlined,
            'Nom complet',
            subtitle: user.fullName,
            color: const Color(0xFF0F172A),
            onTap: _editName,
          ),
          _tile(
            Icons.email_outlined,
            'Adresse e-mail professionnelle',
            subtitle: user.email.isNotEmpty ? user.email : 'Ajouter un e-mail',
            color: const Color(0xFF0F172A),
            onTap: _editEmail,
          ),
          _tile(
            Icons.photo_camera_front_outlined,
            'Modifier la photo de profil',
            subtitle: user.photoUrl != null ? 'Photo configurée' : 'Aucune photo',
            color: const Color(0xFF0D9488),
            onTap: _pickAndUploadPhoto,
          ),
        ]),

        const SizedBox(height: 16),

        // Session & Actions
        _group('SESSION', [
          _tile(
            Icons.logout_rounded,
            'Se déconnecter de la console',
            subtitle: 'Mettre fin à la session administrateur',
            danger: true,
            color: KsgColors.red,
            onTap: _logout,
          ),
        ]),

        const SizedBox(height: 24),
        const Center(
          child: Text(
            'Konaté-Service-Gym • Console Propriétaire v1.6\nBamako, Mali',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11.5, color: Color(0xFF94A3B8), fontWeight: FontWeight.w500),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ── PROFIL CLIENT (COMMANDE, ADRESSES & ASSISTANCE) ──────────────────────────
  // ─────────────────────────────────────────────────────────────────────────────

  Widget _buildClientProfile(User user) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
      children: [
        // Carte d'accueil client
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [KsgColors.green, KsgColors.greenDark],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: const [
              BoxShadow(
                color: Color(0x2E000000),
                blurRadius: 14,
                offset: Offset(0, 6),
              ),
            ],
          ),
          child: Column(
            children: [
              Row(
                children: [
                  _buildAvatar(user, radius: 36),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user.fullName,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 19,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          prettyPhone(user.phone),
                          style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 13),
                        ),
                        if (user.email.isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            user.email,
                            style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
                          ),
                        ],
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                          decoration: BoxDecoration(
                            color: Colors.white24,
                            borderRadius: BorderRadius.circular(100),
                          ),
                          child: const Text(
                            'CLIENT PRIVILÉGIÉ',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 10.5,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              // Bouton direct pour changer de photo
              InkWell(
                onTap: _pickAndUploadPhoto,
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.photo_camera_rounded, size: 16, color: Colors.white),
                      SizedBox(width: 8),
                      Text(
                        'Modifier ma photo de profil',
                        style: TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 16),

        // Résumé client (Commandes & Adresses)
        Row(
          children: [
            Expanded(
              child: _statCard(
                icon: Icons.receipt_long_rounded,
                value: '${user.ordersCount}',
                label: 'Commandes',
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const OrdersScreen()),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _statCard(
                icon: Icons.location_on_rounded,
                value: '${user.addresses.length}',
                label: 'Adresses',
                onTap: () => _showAddresses(user.addresses),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _statCard(
                icon: Icons.account_balance_wallet_outlined,
                value: money(user.totalSpent),
                label: 'Dépensé',
              ),
            ),
          ],
        ),

        const SizedBox(height: 18),

        // Mes Achats & Adresses
        _group('MES COMMANDES & LIVRAISONS', [
          _tile(
            Icons.receipt_long_rounded,
            'Historique de mes commandes',
            subtitle: 'Suivre l\'état et les factures de mes achats',
            color: KsgColors.green,
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const OrdersScreen()),
            ),
          ),
          _tile(
            Icons.location_on_rounded,
            'Mes adresses de livraison (${user.addresses.length})',
            subtitle: 'Gérer vos quartiers et points de repère',
            color: const Color(0xFF2563EB),
            onTap: () => _showAddresses(user.addresses),
          ),
        ]),

        const SizedBox(height: 16),

        // Informations & Sécurité
        _group('INFORMATIONS PERSONNELLES & COMPTE', [
          _tile(
            Icons.edit_rounded,
            'Modifier mon nom',
            subtitle: user.fullName,
            color: const Color(0xFF0F172A),
            onTap: _editName,
          ),
          _tile(
            Icons.email_outlined,
            'Mon adresse e-mail',
            subtitle: user.email.isNotEmpty ? user.email : 'Ajouter un e-mail pour recevoir les reçus',
            color: const Color(0xFF0F172A),
            onTap: _editEmail,
          ),
          _tile(
            Icons.lock_rounded,
            'Changer mon mot de passe',
            subtitle: 'Sécuriser votre accès',
            color: const Color(0xFF475569),
            onTap: _changePassword,
          ),
        ]),

        const SizedBox(height: 16),

        // Assistance WhatsApp
        _group('ASSISTANCE & CONTACT', [
          _tileWhatsApp(
            'Contacter la boutique sur WhatsApp',
            onTap: _contactWhatsApp,
          ),
        ]),

        const SizedBox(height: 16),

        // Zone de déconnexion
        _group('GESTION DU COMPTE', [
          _tile(
            Icons.logout_rounded,
            'Se déconnecter',
            danger: false,
            color: const Color(0xFF64748B),
            onTap: _logout,
          ),
          _tile(
            Icons.delete_rounded,
            'Supprimer mon compte',
            subtitle: 'Supprimer définitivement mes informations personnelles',
            danger: true,
            color: KsgColors.red,
            onTap: _deleteAccount,
          ),
        ]),

        const SizedBox(height: 24),
        const Center(
          child: Text(
            'Konaté-Service-Gym • Bamako, Mali\nApplication v1.0.0',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: KsgColors.muted),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ── STAT CARD WIDGET ────────────────────────────────────────────────────────
  // ─────────────────────────────────────────────────────────────────────────────

  Widget _statCard({
    required IconData icon,
    required String value,
    required String label,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Column(
          children: [
            Icon(icon, size: 20, color: KsgColors.green),
            const SizedBox(height: 6),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: Color(0xFF0F172A)),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600, color: Color(0xFF64748B)),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ── WIDGETS AUXILIAIRES ET LIST TILES ─────────────────────────────────────────
  // ─────────────────────────────────────────────────────────────────────────────

  Widget _group(String title, List<Widget> children) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 6, bottom: 8),
          child: Text(
            title.toUpperCase(),
            style: const TextStyle(
              fontSize: 11,
              letterSpacing: 0.8,
              fontWeight: FontWeight.w800,
              color: Color(0xFF64748B),
            ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            children: [
              for (int i = 0; i < children.length; i++) ...[
                children[i],
                if (i < children.length - 1)
                  const Divider(height: 1, indent: 64, endIndent: 16, color: Color(0xFFF1F5F9)),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _tile(
    IconData icon,
    String label, {
    String? subtitle,
    VoidCallback? onTap,
    bool danger = false,
    Color? color,
    Widget? trailingWidget,
  }) {
    final effectiveColor = danger ? KsgColors.red : (color ?? KsgColors.green);

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: effectiveColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: effectiveColor, size: 21),
      ),
      title: Text(
        label,
        style: TextStyle(
          color: danger ? KsgColors.red : const Color(0xFF0F172A),
          fontWeight: FontWeight.w700,
          fontSize: 14,
        ),
      ),
      subtitle: subtitle != null
          ? Text(
              subtitle,
              style: TextStyle(
                color: danger ? KsgColors.red.withValues(alpha: 0.8) : const Color(0xFF64748B),
                fontSize: 12,
              ),
            )
          : null,
      trailing: trailingWidget ?? const Icon(Icons.chevron_right_rounded, size: 20, color: Color(0xFF94A3B8)),
      onTap: onTap,
    );
  }

  Widget _tileWhatsApp(String label, {VoidCallback? onTap}) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: const Color(0xFF25D366).withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Center(
          child: FaIcon(FontAwesomeIcons.whatsapp, color: Color(0xFF25D366), size: 20),
        ),
      ),
      title: Text(
        label,
        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFF0F172A)),
      ),
      subtitle: const Text(
        'Réponse rapide pour vos questions & conseils',
        style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
      ),
      trailing: const Icon(Icons.chevron_right_rounded, size: 20, color: Color(0xFF94A3B8)),
      onTap: onTap,
    );
  }

  void _showAddresses(List<Address> addresses) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: addresses.isEmpty
              ? const EmptyState(
                  icon: Icons.location_off_outlined,
                  title: 'Aucune adresse enregistrée',
                  message: 'Vous pourrez ajouter une adresse lors du passage de votre commande.',
                )
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Mes adresses de livraison',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 12),
                    for (final address in addresses)
                      Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: ListTile(
                          leading: const Icon(Icons.location_on_rounded, color: KsgColors.green),
                          title: Text(
                            address.label.isEmpty ? address.district : address.label,
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          subtitle: Text(
                            [address.street, address.landmark, address.district]
                                .where((e) => e.isNotEmpty)
                                .join(' · '),
                          ),
                          trailing: address.isDefault
                              ? Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFDCFCE7),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Text(
                                    'Par défaut',
                                    style: TextStyle(
                                      color: Color(0xFF15803D),
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                )
                              : null,
                        ),
                      ),
                  ],
                ),
        ),
      ),
    );
  }

  Future<void> _changePassword() async {
    final current = TextEditingController();
    final next = TextEditingController();
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Changer mon mot de passe'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: current,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Mot de passe actuel'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: next,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Nouveau mot de passe'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Valider')),
        ],
      ),
    );
    if (saved != true || !mounted) return;
    try {
      await context.read<ApiClient>().post('/me/change-password', body: {
        'old_password': current.text,
        'new_password': next.text,
      });
      if (mounted) showMessage(context, 'Mot de passe modifié avec succès.');
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }

  Future<void> _twoFactor(bool enabled) async {
    if (enabled) {
      showMessage(context, 'La double authentification est déjà active sur votre compte.');
      return;
    }
    try {
      final data = await context.read<ApiClient>().post('/auth/2fa/setup');
      if (!mounted) return;
      final map = data as Map<String, dynamic>;
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Activer la double authentification'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Scannez ce QR Code ou entrez ce code secret dans votre application Google Authenticator :'),
              const SizedBox(height: 12),
              SelectableText(
                '${map['secret'] ?? ''}',
                style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.2, color: Color(0xFF0F172A)),
              ),
              const SizedBox(height: 12),
              if (map['otpauth_url'] != null)
                SelectableText(
                  '${map['otpauth_url']}',
                  style: const TextStyle(fontSize: 10.5, color: KsgColors.muted),
                ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Fermer')),
          ],
        ),
      );
    } on ApiException catch (e) {
      if (mounted) showMessage(context, e.message);
    }
  }
}

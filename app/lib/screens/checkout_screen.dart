import 'dart:math';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/repository.dart';
import '../core/format.dart';
import '../core/theme.dart';
import '../models/models.dart';
import '../state/cart_state.dart';
import 'order_detail_screen.dart';

class CheckoutScreen extends StatefulWidget {
  const CheckoutScreen({super.key});

  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  final _note = TextEditingController();
  final _paymentReference = TextEditingController();

  List<Address> _addresses = [];
  Address? _selectedAddress;
  ShopSettings? _settings;
  String _fulfillment = 'delivery';
  String _paymentMethod = 'cash';
  String _slot = '';
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  /// Identifiant d'idempotence : une coupure réseau ne crée pas deux commandes.
  final String _clientReference = _uuid4();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _note.dispose();
    _paymentReference.dispose();
    super.dispose();
  }

  static String _uuid4() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-'
        '${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  Future<void> _load() async {
    final repository = context.read<Repository>();
    try {
      final results = await Future.wait([
        repository.addresses(),
        repository.settings(),
      ]);
      if (!mounted) return;
      final addresses = results[0] as List<Address>;
      final settings = results[1] as ShopSettings;
      Address? defaultAddress;
      for (final address in addresses) {
        if (address.isDefault) {
          defaultAddress = address;
          break;
        }
      }
      setState(() {
        _addresses = addresses;
        _selectedAddress = defaultAddress ?? (addresses.isNotEmpty ? addresses.first : null);
        _settings = settings;
        if (settings.deliverySlots.isNotEmpty) _slot = settings.deliverySlots.first;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addAddress() async {
    final created = await showModalBottomSheet<Address>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _AddressSheet(),
    );
    if (created != null && mounted) {
      setState(() {
        _addresses = [..._addresses, created];
        _selectedAddress = created;
      });
    }
  }

  Future<void> _submit() async {
    if (_fulfillment == 'delivery' && _selectedAddress == null) {
      setState(() => _error = 'Ajoutez une adresse de livraison.');
      return;
    }
    if (_paymentMethod == 'orange_money' && _paymentReference.text.trim().isEmpty) {
      setState(() => _error = 'Indiquez la référence du transfert Orange Money.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final order = await context.read<Repository>().checkout({
        'fulfillment': _fulfillment,
        if (_fulfillment == 'delivery') 'address': _selectedAddress!.id,
        'payment_method': _paymentMethod,
        if (_paymentMethod == 'orange_money')
          'payment_reference': _paymentReference.text.trim(),
        if (_slot.isNotEmpty) 'delivery_slot': _slot,
        if (_note.text.trim().isNotEmpty) 'note': _note.text.trim(),
        'client_reference': _clientReference,
      });
      if (!mounted) return;
      await context.read<CartState>().load(silent: true);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => OrderDetailScreen(orderId: order.id, initial: order)),
      );
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartState>().cart;
    return Scaffold(
      appBar: AppBar(title: const Text('Valider la commande')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                _sectionTitle('Mode de réception'),
                _fulfillmentCard(),
                if (_fulfillment == 'delivery') ...[
                  _sectionTitle('Adresse de livraison'),
                  _addressCard(),
                ],
                _sectionTitle('Paiement'),
                _paymentCard(),
                if (_slot.isNotEmpty) ...[
                  _sectionTitle('Créneau de livraison'),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final slot in _settings?.deliverySlots ?? const <String>[])
                        ChoiceChip(
                          label: Text(slot),
                          selected: _slot == slot,
                          onSelected: (_) => setState(() => _slot = slot),
                        ),
                    ],
                  ),
                ],
                const SizedBox(height: 18),
                TextField(
                  controller: _note,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Note pour la boutique (optionnel)',
                    hintText: 'Ex. appeler avant de livrer',
                  ),
                ),
                const SizedBox(height: 18),
                _summary(cart),
                if (_error != null) ...[
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFBE4E4),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(_error!, style: const TextStyle(color: Color(0xFFB71C1C))),
                  ),
                ],
              ],
            ),
      bottomNavigationBar: _loading
          ? null
          : SafeArea(
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  border: Border(top: BorderSide(color: Color(0xFFEFEBE0))),
                ),
                child: FilledButton(
                  onPressed: _submitting ? null : _submit,
                  child: Text(
                    _submitting ? 'Envoi…' : 'Confirmer · ${money(cart.total)}',
                  ),
                ),
              ),
            ),
    );
  }

  Widget _sectionTitle(String title) => Padding(
        padding: const EdgeInsets.only(top: 18, bottom: 8),
        child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
      );

  Widget _fulfillmentCard() {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Row(
        children: [
          Expanded(
            child: _fulfillmentOption('delivery', Icons.delivery_dining, 'Livraison'),
          ),
          Expanded(
            child: _fulfillmentOption('pickup', Icons.storefront, 'Retrait en boutique'),
          ),
        ],
      ),
    );
  }

  Widget _fulfillmentOption(String value, IconData icon, String label) {
    final selected = _fulfillment == value;
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => setState(() => _fulfillment = value),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: BoxDecoration(
          color: selected ? KsgColors.green.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Icon(icon, color: selected ? KsgColors.green : KsgColors.muted),
            const SizedBox(height: 6),
            Text(
              label,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _addressCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_addresses.isEmpty)
            const Text('Aucune adresse enregistrée.', style: TextStyle(color: KsgColors.muted))
          else
            for (final address in _addresses)
              _choiceTile(
                selected: _selectedAddress?.id == address.id,
                title: address.label.isEmpty ? address.district : address.label,
                subtitle: [address.street, address.landmark, address.district]
                    .where((e) => e.isNotEmpty)
                    .join(' · '),
                onTap: () => setState(() => _selectedAddress = address),
              ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: _addAddress,
              icon: const Icon(Icons.add_location_alt_outlined),
              label: const Text('Ajouter une adresse'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _paymentCard() {
    final orange = _settings?.orangeMoneyPhone ?? '';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _choiceTile(
            selected: _paymentMethod == 'cash',
            title: 'Espèces à la livraison',
            subtitle: 'Payez le livreur à réception.',
            onTap: () => setState(() => _paymentMethod = 'cash'),
          ),
          _choiceTile(
            selected: _paymentMethod == 'orange_money',
            title: 'Orange Money',
            subtitle: orange.isEmpty
                ? 'Transfert puis validation par la boutique.'
                : 'Transférez au $orange puis saisissez la référence.',
            onTap: () => setState(() => _paymentMethod = 'orange_money'),
          ),
          if (_paymentMethod == 'orange_money')
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: TextField(
                controller: _paymentReference,
                decoration: const InputDecoration(
                  labelText: 'Référence du transfert',
                  hintText: 'Ex. OM-2026-00123',
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _choiceTile({
    required bool selected,
    required String title,
    String? subtitle,
    required VoidCallback onTap,
  }) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              selected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
              size: 20,
              color: selected ? KsgColors.green : KsgColors.muted,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
                  if (subtitle != null && subtitle.isNotEmpty)
                    Text(
                      subtitle,
                      style: const TextStyle(fontSize: 12.5, color: KsgColors.muted),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _summary(Cart cart) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('${cart.itemCount} article(s)'),
              Text(money(cart.subtotal)),
            ],
          ),
          if (cart.discount > 0)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Remise'),
                Text('- ${money(cart.discount)}', style: const TextStyle(color: KsgColors.green)),
              ],
            ),
          const Divider(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Total', style: TextStyle(fontWeight: FontWeight.w800)),
              Text(
                money(cart.total),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Formulaire d'ajout d'adresse (bottom sheet).
class _AddressSheet extends StatefulWidget {
  const _AddressSheet();

  @override
  State<_AddressSheet> createState() => _AddressSheetState();
}

class _AddressSheetState extends State<_AddressSheet> {
  final _formKey = GlobalKey<FormState>();
  final _label = TextEditingController(text: 'Maison');
  final _district = TextEditingController();
  final _street = TextEditingController();
  final _landmark = TextEditingController();
  final _phone = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _label.dispose();
    _district.dispose();
    _street.dispose();
    _landmark.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final address = await context.read<Repository>().createAddress({
        'label': _label.text.trim(),
        'district': _district.text.trim(),
        'street': _street.text.trim(),
        'landmark': _landmark.text.trim(),
        if (_phone.text.trim().isNotEmpty) 'phone': normalizePhoneInput(_phone.text),
        'is_default': false,
      });
      if (mounted) Navigator.pop(context, address);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Nouvelle adresse',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _label,
              decoration: const InputDecoration(labelText: 'Libellé (Maison, Bureau…)'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _district,
              decoration: const InputDecoration(labelText: 'Quartier *'),
              validator: (value) =>
                  (value == null || value.trim().isEmpty) ? 'Indiquez le quartier.' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _street,
              decoration: const InputDecoration(labelText: 'Rue / porte'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _landmark,
              decoration: const InputDecoration(labelText: 'Point de repère'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Téléphone sur place'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: KsgColors.red)),
            ],
            const SizedBox(height: 18),
            FilledButton(
              onPressed: _saving ? null : _save,
              child: Text(_saving ? 'Enregistrement…' : 'Enregistrer l\'adresse'),
            ),
          ],
        ),
      ),
    );
  }
}

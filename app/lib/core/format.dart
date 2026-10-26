import 'package:intl/intl.dart';

final _money = NumberFormat.decimalPattern('fr_FR');
final _shortDate = DateFormat('dd/MM/yyyy', 'fr_FR');
final _longDate = DateFormat('dd MMM yyyy à HH:mm', 'fr_FR');

/// 48000 -> « 48 000 FCFA ».
String money(int amount, {String currency = 'FCFA'}) =>
    '${_money.format(amount)} $currency';

String shortDate(DateTime? date) => date == null ? '—' : _shortDate.format(date.toLocal());

String longDate(DateTime? date) => date == null ? '—' : _longDate.format(date.toLocal());

/// Numéro malien affichable : 70000000 -> +223 70 00 00 00.
String prettyPhone(String raw) {
  final digits = raw.replaceAll(RegExp(r'[^0-9]'), '');
  final local = digits.length > 8 ? digits.substring(digits.length - 8) : digits;
  if (local.length != 8) return raw;
  final groups = [local.substring(0, 2), local.substring(2, 4), local.substring(4, 6), local.substring(6)];
  return '+223 ${groups.join(' ')}';
}

/// Normalise un numéro saisi → format complet malien 11 chiffres (223XXXXXXXX)
/// attendu par le backend Django.
/// Exemples :
///   "70 00 00 00"  → "22370000000"
///   "+223 70 00 00 00" → "22370000000"
///   "22370000000"  → "22370000000"
String normalizePhoneInput(String input) {
  final digits = input.replaceAll(RegExp(r'[^0-9]'), '');
  // Déjà au format complet 223XXXXXXXX
  if (digits.startsWith('223') && digits.length == 11) return digits;
  // Format local 8 chiffres → on préfixe avec 223
  if (digits.length == 8) return '223$digits';
  return digits;
}

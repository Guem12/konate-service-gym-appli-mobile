import 'dart:typed_data';
import '../models/models.dart';
import 'api_client.dart';

/// Accès en lecture/écriture aux ressources de la boutique.
class Repository {
  Repository(this.api);

  final ApiClient api;

  Future<HomeData> home() async {
    final data = await api.get('/home');
    return HomeData.fromJson(data as Map<String, dynamic>);
  }

  Future<ShopSettings> settings() async {
    final data = await api.get('/settings');
    return ShopSettings.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Category>> categories() async {
    final data = await api.get('/categories');
    final list = data is Map ? (data['results'] as List<dynamic>? ?? []) : (data as List<dynamic>);
    return list.map((e) => Category.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<({List<Product> products, int count})> products({
    String search = '',
    int? categoryId,
    bool onlyPromotions = false,
    String ordering = '-sold_count',
    int page = 1,
  }) async {
    final data = await api.get('/products', query: {
      if (search.trim().isNotEmpty) 'search': search.trim(),
      'category': ?categoryId,
      if (onlyPromotions) 'promotion': 'true',
      'ordering': ordering,
      'page': page,
    });
    final map = data is Map<String, dynamic> ? data : <String, dynamic>{'results': data};
    final results = (map['results'] as List<dynamic>? ?? [])
        .map((e) => Product.fromJson(e as Map<String, dynamic>))
        .toList();
    return (products: results, count: _count(map, results.length));
  }

  Future<Product> product(int id) async {
    final data = await api.get('/products/$id');
    return Product.fromJson(data as Map<String, dynamic>);
  }

  Future<bool> toggleFavorite(int productId) async {
    final data = await api.post('/me/favorites/toggle', body: {'product': productId});
    return data is Map && data['is_favorite'] == true;
  }

  Future<List<OrderSummary>> orders() async {
    final data = await api.get('/orders');
    final map = data is Map<String, dynamic> ? data : <String, dynamic>{'results': []};
    return (map['results'] as List<dynamic>? ?? [])
        .map((e) => OrderSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<OrderSummary>> ordersReceiptRegister({
    String? clientFilter,
    String? dateFrom,
    String? dateTo,
    String? paymentStatus,
    String? kind,
  }) async {
    final data = await api.get('/admin/orders/receipts', query: {
      if (clientFilter?.isNotEmpty == true) 'search': clientFilter,
      if (dateFrom?.isNotEmpty == true) 'date_from': dateFrom,
      if (dateTo?.isNotEmpty == true) 'date_to': dateTo,
      if (paymentStatus != null && paymentStatus != 'all') 'payment_status': paymentStatus,
      if (kind != null && kind != 'all') 'kind': kind,
    });
    final map = data is Map<String, dynamic> ? data : <String, dynamic>{'results': []};
    return (map['results'] as List<dynamic>? ?? [])
        .map((e) => OrderSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<OrderDetail> order(int id) async {
    final data = await api.get('/orders/$id');
    return OrderDetail.fromJson(data as Map<String, dynamic>);
  }

  Future<OrderDetail> checkout(Map<String, dynamic> payload) async {
    final data = await api.post('/orders', body: payload);
    return OrderDetail.fromJson(data as Map<String, dynamic>);
  }

  Future<void> cancelOrder(int id, String reason) =>
      api.post('/orders/$id/cancel', body: {'reason': reason});

  Future<String> whatsappLink({int? productId, int? variantId}) async {
    final query = <String, dynamic>{};
    if (productId != null) query['product'] = productId;
    if (variantId != null) query['variant'] = variantId;
    final data = await api.get('/whatsapp/link', query: query);
    return data is Map ? '${data['url'] ?? ''}' : '';
  }

  Future<DashboardData> dashboard() async {
    final data = await api.get('/admin/dashboard');
    return DashboardData.fromJson(data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> reports({String? dateFrom, String? dateTo}) async {
    final query = <String, dynamic>{};
    if (dateFrom != null) query['date_from'] = dateFrom;
    if (dateTo != null) query['date_to'] = dateTo;
    final data = await api.get('/admin/reports', query: query);
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }

  Future<List<OrderSummary>> adminOrders({String status = '', String search = ''}) async {
    final data = await api.get('/admin/orders', query: {
      if (status.isNotEmpty) 'status': status,
      if (search.isNotEmpty) 'search': search,
    });
    final map = data is Map<String, dynamic> ? data : <String, dynamic>{'results': []};
    return (map['results'] as List<dynamic>? ?? [])
        .map((e) => OrderSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> updateOrderStatus(int id, String status) =>
      api.post('/admin/orders/$id/status', body: {'status': status});

  Future<List<Delivery>> deliveries({String status = ''}) async {
    final data = await api.get('/admin/deliveries', query: {
      if (status.isNotEmpty) 'status': status,
    });
    final map = data is Map<String, dynamic> ? data : <String, dynamic>{'results': []};
    return (map['results'] as List<dynamic>? ?? [])
        .map((e) => Delivery.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> updateDelivery(int id, Map<String, dynamic> payload) =>
      api.patch('/admin/deliveries/$id', body: payload);

  Future<List<Product>> adminProducts({String search = ''}) async {
    final data = await api.get('/admin/products', query: {
      if (search.isNotEmpty) 'search': search,
    });
    final map = data is Map<String, dynamic> ? data : <String, dynamic>{'results': []};
    return (map['results'] as List<dynamic>? ?? [])
        .map((e) => Product.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> toggleProductPublished(int id, bool publish) =>
      api.patch('/admin/products/$id', body: {
        'status': publish ? 'published' : 'draft',
      });

  Future<void> adjustStock(int variantId, int quantity, String reason) =>
      api.post('/admin/stock-movements', body: {
        'variant': variantId,
        'movement_type': quantity >= 0 ? 'restock' : 'adjustment',
        'quantity': quantity,
        'reason': reason,
      });

  Future<({int count, int total, List<PaymentInfo> results})> pendingPayments() async {
    final data = await api.get('/admin/payments/pending');
    final map = data is Map<String, dynamic> ? data : <String, dynamic>{};
    final results = (map['results'] as List<dynamic>? ?? [])
        .map((e) => PaymentInfo.fromJson(e as Map<String, dynamic>))
        .toList();
    final total = map['total'];
    return (
      count: results.length,
      total: total is int ? total : 0,
      results: results,
    );
  }

  Future<Uint8List> exportPDF({required String type, required String dateFrom, required String dateTo}) async {
    final data = await api.get('/admin/reports/export', query: {
      'type': type,
      'date_from': dateFrom,
      'date_to': dateTo,
    });
    if (data is! List<int>) {
      throw ApiException('Erreur lors de l'export PDF');
    }
    return data as Uint8List;
  }

  Future<PaymentInfo> confirmPayment(int paymentId) async {
    final data = await api.post('/admin/payments/$paymentId/confirm');
    return PaymentInfo.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Address>> addresses() async {
    final data = await api.get('/me/addresses');
    final list = data is Map ? (data['results'] as List<dynamic>? ?? []) : data as List<dynamic>;
    return list.map((e) => Address.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Address> createAddress(Map<String, dynamic> payload) async {
    final data = await api.post('/me/addresses', body: payload);
    return Address.fromJson(data as Map<String, dynamic>);
  }

  Future<void> deleteAddress(int id) => api.delete('/me/addresses/$id');

  int _count(Map<String, dynamic> map, int fallback) {
    final count = map['count'];
    return count is int ? count : fallback;
  }
}

/// Modèles de données alignés sur les réponses de l'API Django.
/// Les montants sont des entiers en francs CFA (XOF) : aucun flottant pour
/// éviter les erreurs d'arrondi sur l'argent.
library;

import '../core/product_assets.dart';

int _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.round();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}

String _asString(dynamic value, [String fallback = '']) =>
    value == null ? fallback : '$value';

class User {
  User({
    required this.id,
    required this.phone,
    required this.fullName,
    this.email = '',
    this.photoUrl,
    this.role = 'client',
    this.isBlocked = false,
    this.twoFactorEnabled = false,
    this.addresses = const [],
    this.ordersCount = 0,
    this.totalSpent = 0,
    this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: _asInt(json['id']),
        phone: _asString(json['phone']),
        fullName: _asString(json['full_name'], 'Client'),
        email: _asString(json['email']),
        photoUrl: json['photo_url'] as String?,
        role: _asString(json['role'], 'client'),
        isBlocked: json['is_blocked'] == true,
        twoFactorEnabled: json['two_factor_enabled'] == true,
        addresses: (json['addresses'] as List<dynamic>? ?? [])
            .map((e) => Address.fromJson(e as Map<String, dynamic>))
            .toList(),
        ordersCount: _asInt(json['orders_count']),
        totalSpent: _asInt(json['total_spent']),
        createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
      );

  final int id;
  final String phone;
  final String fullName;
  final String email;
  final String? photoUrl;
  final String role;
  final bool isBlocked;
  final bool twoFactorEnabled;
  final List<Address> addresses;
  final int ordersCount;
  final int totalSpent;
  final DateTime? createdAt;

  String get phoneDisplay => '+223 $phone'.replaceFirst('+223 223', '+223');

  bool get isStaff => role == 'owner' || role == 'manager' || role == 'vendor';
  bool get isOwner => role == 'owner';

  String get roleLabel => switch (role) {
        'owner' => 'Propriétaire',
        'manager' => 'Gérant',
        'vendor' => 'Vendeur',
        _ => 'Client',
      };
}

class Address {
  Address({
    required this.id,
    required this.district,
    this.label = '',
    this.street = '',
    this.landmark = '',
    this.phone = '',
    this.isDefault = false,
  });

  factory Address.fromJson(Map<String, dynamic> json) => Address(
        id: _asInt(json['id']),
        district: _asString(json['district']),
        label: _asString(json['label']),
        street: _asString(json['street']),
        landmark: _asString(json['landmark']),
        phone: _asString(json['phone']),
        isDefault: json['is_default'] == true,
      );

  final int id;
  final String district;
  final String label;
  final String street;
  final String landmark;
  final String phone;
  final bool isDefault;

  String get summary =>
      [label, street, district]
          .where((e) => e.trim().isNotEmpty)
          .join(' · ');
}

class Category {
  Category({
    required this.id,
    required this.name,
    this.slug = '',
    this.imageUrl,
    this.productCount = 0,
    this.children = const [],
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    final slug = _asString(json['slug']);
    final id = _asInt(json['id']);
    final name = _asString(json['name']);
    final assetImg = CategoryAssets.getImage(slug: slug, id: id, name: name);

    return Category(
      id: id,
      name: name,
      slug: slug,
      imageUrl: assetImg ?? json['image_url'] as String?,
      productCount: _asInt(json['product_count']),
      children: (json['children'] as List<dynamic>? ?? [])
          .map((e) => Category.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final int id;
  final String name;
  final String slug;
  final String? imageUrl;
  final int productCount;
  final List<Category> children;
}

class ProductVariant {
  ProductVariant({
    required this.id,
    required this.label,
    required this.price,
    required this.stockQty,
    this.sku = '',
    this.attributes = const {},
    this.isActive = true,
  });

  factory ProductVariant.fromJson(Map<String, dynamic> json) => ProductVariant(
        id: _asInt(json['id']),
        label: _asString(json['label']),
        price: _asInt(json['price_sale']),
        stockQty: _asInt(json['stock_qty']),
        sku: _asString(json['sku']),
        attributes: Map<String, dynamic>.from(json['attributes'] as Map? ?? {}),
        isActive: json['is_active'] != false,
      );

  final int id;
  final String label;
  final int price;
  final int stockQty;
  final String sku;
  final Map<String, dynamic> attributes;
  final bool isActive;

  bool get inStock => stockQty > 0;
}

class Product {
  Product({
    required this.id,
    required this.name,
    required this.slug,
    required this.price,
    this.comparePrice,
    this.imageUrl,
    this.categoryId,
    this.categoryName = '',
    this.brandName = '',
    this.description = '',
    this.stockStatus = 'in_stock',
    this.status = 'published',
    this.isFavorite = false,
    this.isNew = false,
    this.warrantyMonths = 0,
    this.variants = const [],
    this.images = const [],
    this.characteristics = const [],
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    final slug = _asString(json['slug']);
    final id = _asInt(json['id']);
    final name = _asString(json['name']);
    final assetImage = ProductAssets.getPrimaryImage(slug: slug, id: id, name: name);
    final assetGallery = ProductAssets.getGallery(slug: slug, id: id, name: name);

    final rawImages = [
      for (final image in (json['images'] as List<dynamic>? ?? []))
        if ((image as Map<String, dynamic>)['url'] != null)
          '${image['url']}'
    ];

    final finalImageUrl = assetImage ?? json['primary_image'] as String?;
    final finalImages = assetGallery.isNotEmpty
        ? assetGallery
        : (rawImages.isNotEmpty ? rawImages : [?finalImageUrl]);

    return Product(
      id: id,
      name: name,
      slug: slug,
      price: _asInt(json['price']),
      comparePrice:
          json['compare_price'] == null ? null : _asInt(json['compare_price']),
      imageUrl: finalImageUrl,
      categoryId:
          json['category'] == null ? null : _asInt(json['category']),
      categoryName: _asString(json['category_name']),
      brandName: _asString(json['brand_name']),
      description: _asString(json['description']),
      stockStatus: _asString(json['stock_status'], 'in_stock'),
      status: _asString(json['status'], 'published'),
      isFavorite: json['is_favorite'] == true,
      isNew: json['is_new'] == true,
      warrantyMonths: _asInt(json['warranty_months']),
      variants: (json['variants'] as List<dynamic>? ?? [])
          .map((e) => ProductVariant.fromJson(e as Map<String, dynamic>))
          .toList(),
      images: finalImages,
      characteristics: (json['characteristics_list'] as List<dynamic>? ?? [])
          .map((e) => '$e')
          .toList(),
    );
  }

  final int id;
  final String name;
  final String slug;
  final int price;
  final int? comparePrice;
  final String? imageUrl;
  final int? categoryId;
  final String categoryName;
  final String brandName;
  final String description;
  final String stockStatus;
  final String status;
  final bool isFavorite;

  bool get isPublished => status == 'published';
  final bool isNew;
  final int warrantyMonths;
  final List<ProductVariant> variants;
  final List<String> images;
  final List<String> characteristics;

  bool get inStock => stockStatus != 'out_of_stock';
  bool get hasPromotion => comparePrice != null && comparePrice! > price;
}

class CartItem {
  CartItem({
    required this.id,
    required this.variantId,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    this.variantLabel = '',
    this.imageUrl,
    this.stockQty = 0,
  });

  factory CartItem.fromJson(Map<String, dynamic> json) => CartItem(
        id: _asInt(json['id']),
        variantId: _asInt(json['variant']),
        productName: _asString(json['product_name']),
        quantity: _asInt(json['quantity']),
        unitPrice: _asInt(json['unit_price']),
        variantLabel: _asString(json['variant_label']),
        imageUrl: ProductAssets.getPrimaryImage(name: _asString(json['product_name'])) ?? json['image'] as String?,
        stockQty: _asInt(json['stock_qty']),
      );

  final int id;
  final int variantId;
  final String productName;
  final int quantity;
  final int unitPrice;
  final String variantLabel;
  final String? imageUrl;
  final int stockQty;

  int get lineTotal => unitPrice * quantity;
}

class Cart {
  Cart({
    this.items = const [],
    this.subtotal = 0,
    this.discount = 0,
    this.total = 0,
    this.itemCount = 0,
    this.couponCode = '',
  });

  factory Cart.fromJson(Map<String, dynamic> json) => Cart(
        items: (json['items'] as List<dynamic>? ?? [])
            .map((e) => CartItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        subtotal: _asInt(json['subtotal']),
        discount: _asInt(json['discount']),
        total: _asInt(json['total']),
        itemCount: _asInt(json['item_count']),
        couponCode: _asString(json['coupon_code']),
      );

  final List<CartItem> items;
  final int subtotal;
  final int discount;
  final int total;
  final int itemCount;
  final String couponCode;

  bool get isEmpty => items.isEmpty;
}

class OrderSummary {
  OrderSummary({
    required this.id,
    required this.number,
    required this.status,
    required this.statusLabel,
    required this.total,
    this.amountPaid = 0,
    this.balanceDue = 0,
    this.itemCount = 0,
    this.imageUrl,
    this.itemNames = const [],
    this.canCancel = false,
    this.fulfillment = 'delivery',
    this.createdAt,
  });

  factory OrderSummary.fromJson(Map<String, dynamic> json) => OrderSummary(
        id: _asInt(json['id']),
        number: _asString(json['number']),
        status: _asString(json['status']),
        statusLabel:
            _asString(json['status_display'], _asString(json['status'])),
        total: _asInt(json['total']),
        amountPaid: _asInt(json['amount_paid']),
        balanceDue: _asInt(json['balance_due']),
        itemCount: _asInt(json['item_count']),
        imageUrl: json['image'] as String?,
        itemNames: (json['item_names'] as List<dynamic>? ?? [])
            .map((e) => '$e')
            .toList(),
        canCancel: json['can_cancel'] == true,
        fulfillment: _asString(json['fulfillment'], 'delivery'),
        createdAt: DateTime.tryParse(_asString(json['created_at'])),
      );

  final int id;
  final String number;
  final String status;
  final String statusLabel;
  final int total;
  final int amountPaid;
  final int balanceDue;
  final int itemCount;
  final String? imageUrl;
  final List<String> itemNames;
  final bool canCancel;
  final String fulfillment;
  final DateTime? createdAt;

  bool get isOpen =>
      !['delivered', 'cancelled', 'returned'].contains(status);
}

class OrderLine {
  OrderLine({
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    this.variantLabel = '',
  });

  factory OrderLine.fromJson(Map<String, dynamic> json) => OrderLine(
        productName: _asString(json['product_name']),
        quantity: _asInt(json['quantity']),
        unitPrice: _asInt(json['unit_price_sale']),
        variantLabel: _asString(json['variant_label']),
      );

  final String productName;
  final int quantity;
  final int unitPrice;
  final String variantLabel;

  int get lineTotal => quantity * unitPrice;
}

class OrderDetail extends OrderSummary {
  OrderDetail({
    required super.id,
    required super.number,
    required super.status,
    required super.statusLabel,
    required super.total,
    super.amountPaid,
    super.balanceDue,
    super.itemCount,
    super.imageUrl,
    super.canCancel,
    super.createdAt,
    this.lines = const [],
    this.timeline = const [],
    this.customerName = '',
    this.customerPhone = '',
    this.deliveryAddress = '',
    this.deliverySlot = '',
    this.note = '',
    this.subtotal = 0,
    this.discount = 0,
    this.deliveryFee = 0,
    this.whatsappUrl = '',
    this.paymentMethod = '',
  });

  factory OrderDetail.fromJson(Map<String, dynamic> json) {
    final summary = OrderSummary.fromJson(json);
    final payments = json['payments'] as List<dynamic>? ?? [];
    return OrderDetail(
      id: summary.id,
      number: summary.number,
      status: summary.status,
      statusLabel: summary.statusLabel,
      total: summary.total,
      amountPaid: summary.amountPaid,
      balanceDue: summary.balanceDue,
      itemCount: summary.itemCount,
      imageUrl: summary.imageUrl,
      canCancel: summary.canCancel,
      createdAt: summary.createdAt,
      lines: (json['items'] as List<dynamic>? ?? [])
          .map((e) => OrderLine.fromJson(e as Map<String, dynamic>))
          .toList(),
      timeline: (json['timeline'] as List<dynamic>? ?? [])
          .map((e) => TimelineEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      customerName: _asString(json['customer_name']),
      customerPhone: _asString(json['customer_phone']),
      deliveryAddress: _asString(json['delivery_address']),
      deliverySlot: _asString(json['delivery_slot']),
      note: _asString(json['note']),
      subtotal: _asInt(json['subtotal']),
      discount: _asInt(json['discount']),
      deliveryFee: _asInt(json['delivery_fee']),
      whatsappUrl: _asString(json['whatsapp_url']),
      paymentMethod: payments.isEmpty
          ? ''
          : _asString(payments.first['method']),
    );
  }

  final List<OrderLine> lines;
  final List<TimelineEntry> timeline;
  final String customerName;
  final String customerPhone;
  final String deliveryAddress;
  final String deliverySlot;
  final String note;
  final int subtotal;
  final int discount;
  final int deliveryFee;
  final String whatsappUrl;
  final String paymentMethod;
}

class TimelineEntry {
  TimelineEntry({
    required this.status,
    required this.label,
    this.note = '',
    this.userName = '',
    this.createdAt,
  });

  factory TimelineEntry.fromJson(Map<String, dynamic> json) => TimelineEntry(
        status: _asString(json['status']),
        label: _asString(json['status_display'], _asString(json['status'])),
        note: _asString(json['note']),
        userName: _asString(json['user_name']),
        createdAt: DateTime.tryParse(_asString(json['created_at'])),
      );

  final String status;
  final String label;
  final String note;
  final String userName;
  final DateTime? createdAt;
}

class Delivery {
  Delivery({
    required this.id,
    required this.orderNumber,
    required this.status,
    required this.statusLabel,
    this.customerName = '',
    this.customerPhone = '',
    this.courierName = '',
    this.addressText = '',
    this.slot = '',
    this.zone = '',
    this.total = 0,
    this.balanceDue = 0,
  });

  factory Delivery.fromJson(Map<String, dynamic> json) => Delivery(
        id: _asInt(json['id']),
        orderNumber: _asString(json['order_number']),
        status: _asString(json['status']),
        statusLabel:
            _asString(json['status_display'], _asString(json['status'])),
        customerName: _asString(json['customer_name']),
        customerPhone: _asString(json['customer_phone']),
        courierName: _asString(json['courier_name']),
        addressText: _asString(json['address_text']),
        slot: _asString(json['slot']),
        zone: _asString(json['zone']),
        total: _asInt(json['total']),
        balanceDue: _asInt(json['balance_due']),
      );

  final int id;
  final String orderNumber;
  final String status;
  final String statusLabel;
  final String customerName;
  final String customerPhone;
  final String courierName;
  final String addressText;
  final String slot;
  final String zone;
  final int total;
  final int balanceDue;

  bool get isDelivered => status == 'delivered';
}

class PaymentInfo {
  PaymentInfo({
    required this.id,
    required this.orderId,
    required this.orderNumber,
    required this.amount,
    required this.methodLabel,
    required this.status,
    required this.statusLabel,
    this.customerName = '',
    this.reference = '',
    this.payerPhone = '',
    this.createdAt,
  });

  factory PaymentInfo.fromJson(Map<String, dynamic> json) => PaymentInfo(
        id: _asInt(json['id']),
        orderId: _asInt(json['order']),
        orderNumber: _asString(json['order_number']),
        amount: _asInt(json['amount']),
        methodLabel:
            _asString(json['method_display'], _asString(json['method'])),
        status: _asString(json['status']),
        statusLabel:
            _asString(json['status_display'], _asString(json['status'])),
        customerName: _asString(json['customer_name']),
        reference: _asString(json['om_reference']),
        payerPhone: _asString(json['payer_phone']),
        createdAt: DateTime.tryParse(_asString(json['created_at'])),
      );

  final int id;
  final int orderId;
  final String orderNumber;
  final int amount;
  final String methodLabel;
  final String status;
  final String statusLabel;
  final String customerName;
  final String reference;
  final String payerPhone;
  final DateTime? createdAt;

  bool get isPending => status == 'pending';
}

class ShopSettings {
  ShopSettings({
    this.shopName = 'Konaté-Service-Gym',
    this.whatsappPhone = '',
    this.orangeMoneyPhone = '',
    this.address = '',
    this.openingHours = '',
    this.deliveryNote = '',
    this.deliveryZones = const [],
    this.deliverySlots = const [],
    this.freeDelivery = false,
    this.returnDelayDays = 7,
    this.currency = 'FCFA',
  });

  factory ShopSettings.fromJson(Map<String, dynamic> json) => ShopSettings(
        shopName: _asString(json['shop_name'], 'Konaté-Service-Gym'),
        whatsappPhone: _asString(json['whatsapp_phone']),
        orangeMoneyPhone: _asString(json['orange_money_phone']),
        address: _asString(json['address']),
        openingHours: _asString(json['opening_hours']),
        deliveryNote: _asString(json['delivery_note']),
        deliveryZones: [
          for (final zone in (json['delivery_zones'] as List<dynamic>? ?? []))
            '${(zone as Map<String, dynamic>)['name'] ?? zone}'
        ],
        deliverySlots: (json['delivery_slots'] as List<dynamic>? ?? [])
            .map((e) => '$e')
            .toList(),
        freeDelivery: json['free_delivery'] == true,
        returnDelayDays: _asInt(json['return_delay_days']),
        currency: _asString(json['currency'], 'FCFA'),
      );

  final String shopName;
  final String whatsappPhone;
  final String orangeMoneyPhone;
  final String address;
  final String openingHours;
  final String deliveryNote;
  final List<String> deliveryZones;
  final List<String> deliverySlots;
  final bool freeDelivery;
  final int returnDelayDays;
  final String currency;
}

class Banner {
  Banner({
    required this.id,
    required this.title,
    this.subtitle = '',
    this.imageUrl,
    this.discountLabel = '',
  });

  factory Banner.fromJson(Map<String, dynamic> json) => Banner(
        id: _asInt(json['id']),
        title: _asString(json['name'] ?? json['title'], 'Promotion'),
        subtitle: _asString(json['description']),
        imageUrl: json['image_url'] as String?,
        discountLabel: _asString(json['discount_label']),
      );

  final int id;
  final String title;
  final String subtitle;
  final String? imageUrl;
  final String discountLabel;
}

class HomeData {
  HomeData({
    this.banners = const [],
    this.categories = const [],
    this.popular = const [],
    this.newArrivals = const [],
    this.promotions = const [],
    this.featured = const [],
  });

  factory HomeData.fromJson(Map<String, dynamic> json) {
    List<Product> products(String key) => (json[key] as List<dynamic>? ?? [])
        .map((e) => Product.fromJson(e as Map<String, dynamic>))
        .toList();
    return HomeData(
      banners: (json['banners'] as List<dynamic>? ?? [])
          .map((e) => Banner.fromJson(e as Map<String, dynamic>))
          .toList(),
      categories: (json['categories'] as List<dynamic>? ?? [])
          .map((e) => Category.fromJson(e as Map<String, dynamic>))
          .toList(),
      popular: products('popular'),
      newArrivals: products('new'),
      promotions: products('promotions'),
      featured: products('featured'),
    );
  }

  final List<Banner> banners;
  final List<Category> categories;
  final List<Product> popular;
  final List<Product> newArrivals;
  final List<Product> promotions;
  final List<Product> featured;
}

class DashboardData {
  DashboardData({
    this.revenueToday = 0,
    this.ordersToday = 0,
    this.pendingOrders = 0,
    this.lowStock = const [],
    this.topProducts = const [],
    this.revenueWeek = const [],
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    final today = Map<String, dynamic>.from(json['today'] as Map? ?? {});
    return DashboardData(
      revenueToday: _asInt(today['revenue']),
      ordersToday: _asInt(today['orders']),
      pendingOrders: _asInt(json['pending_orders'] ?? json['orders_to_prepare']),
      lowStock: (json['low_stock'] as List<dynamic>? ?? [])
          .map((e) => LowStockItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      topProducts: (json['top_products'] as List<dynamic>? ?? [])
          .map((e) => TopProduct.fromJson(e as Map<String, dynamic>))
          .toList(),
      revenueWeek: (json['revenue_week'] as List<dynamic>? ?? [])
          .map((e) => RevenuePoint.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final int revenueToday;
  final int ordersToday;
  final int pendingOrders;
  final List<LowStockItem> lowStock;
  final List<TopProduct> topProducts;
  final List<RevenuePoint> revenueWeek;
}

class LowStockItem {
  LowStockItem({required this.name, required this.stock, this.threshold = 0});

  factory LowStockItem.fromJson(Map<String, dynamic> json) => LowStockItem(
        name: _asString(json['name']),
        stock: _asInt(json['stock_qty'] ?? json['stock']),
        threshold: _asInt(json['low_stock_threshold'] ?? json['threshold']),
      );

  final String name;
  final int stock;
  final int threshold;
}

class TopProduct {
  TopProduct({required this.name, required this.soldCount});

  factory TopProduct.fromJson(Map<String, dynamic> json) => TopProduct(
        name: _asString(json['name']),
        soldCount: _asInt(json['sold_count']),
      );

  final String name;
  final int soldCount;
}

class RevenuePoint {
  RevenuePoint({required this.label, required this.value});

  factory RevenuePoint.fromJson(Map<String, dynamic> json) => RevenuePoint(
        label: _asString(json['date'] ?? json['label']),
        value: _asInt(json['total'] ?? json['value']),
      );

  final String label;
  final int value;
}
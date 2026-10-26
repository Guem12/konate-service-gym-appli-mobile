import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/auth_state.dart';
import '../state/cart_state.dart';
import '../core/theme.dart';
import 'admin/admin_home.dart';
import 'cart_screen.dart';
import 'catalog_screen.dart';
import 'home_screen.dart';
import 'orders_screen.dart';
import 'profile_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<CartState>().load(silent: true);
    });
  }

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartState>();
    final isStaff = context.watch<AuthState>().isStaff;

    final pages = <Widget>[
      const HomeScreen(),
      const CatalogScreen(),
      const CartScreen(),
      const OrdersScreen(),
      const ProfileScreen(),
      if (isStaff) AdminHomeScreen(onExitAdmin: () => setState(() => _index = 0)),
    ];

    final destinations = <NavigationDestination>[
      const NavigationDestination(
        icon: Icon(Icons.storefront_outlined),
        selectedIcon: Icon(Icons.storefront_rounded),
        label: 'Accueil',
      ),
      const NavigationDestination(
        icon: Icon(Icons.grid_view_outlined),
        selectedIcon: Icon(Icons.grid_view_rounded),
        label: 'Catalogue',
      ),
      NavigationDestination(
        icon: Badge(
          isLabelVisible: cart.itemCount > 0,
          label: Text('${cart.itemCount}'),
          backgroundColor: KsgColors.green,
          textColor: Colors.white,
          child: const Icon(Icons.shopping_bag_outlined),
        ),
        selectedIcon: Badge(
          isLabelVisible: cart.itemCount > 0,
          label: Text('${cart.itemCount}'),
          backgroundColor: KsgColors.green,
          textColor: Colors.white,
          child: const Icon(Icons.shopping_bag_rounded),
        ),
        label: 'Panier',
      ),
      const NavigationDestination(
        icon: Icon(Icons.receipt_long_outlined),
        selectedIcon: Icon(Icons.receipt_long_rounded),
        label: 'Commandes',
      ),
      const NavigationDestination(
        icon: Icon(Icons.person_outline_rounded),
        selectedIcon: Icon(Icons.person_rounded),
        label: 'Profil',
      ),
      if (isStaff)
        const NavigationDestination(
          icon: Icon(Icons.admin_panel_settings_outlined),
          selectedIcon: Icon(Icons.admin_panel_settings_rounded),
          label: 'Gestion',
        ),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: (isStaff && _index == 5)
          ? null
          : Container(
              decoration: BoxDecoration(
                color: KsgColors.surface,
                boxShadow: [
                  BoxShadow(
                    color: KsgColors.navy.withValues(alpha: 0.08),
                    blurRadius: 20,
                    offset: const Offset(0, -4),
                  ),
                ],
              ),
              child: NavigationBar(
                selectedIndex: _index,
                onDestinationSelected: (value) => setState(() => _index = value),
                destinations: destinations,
              ),
            ),
    );
  }
}

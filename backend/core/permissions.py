"""Permissions par rôle."""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class IsOwner(permissions.BasePermission):
    message = "Cette action est réservée au propriétaire de la boutique."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "owner")


class IsStaffRole(permissions.BasePermission):
    """Propriétaire, vendeur ou gestionnaire de stock : accès administration."""

    message = "Un compte d'administration est requis."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff_role)


class IsVendorOrOwner(IsStaffRole):
    message = "Cette action est réservée aux vendeurs et au propriétaire."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            super().has_permission(request, view)
            and user.role in {"owner", "vendor"}
        )


class IsStockManagerOrOwner(IsStaffRole):
    message = "Cette action est réservée aux gestionnaires de stock et au propriétaire."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            super().has_permission(request, view)
            and user.role in {"owner", "stock_manager"}
        )


class IsAdminRole(IsStaffRole):
    """Seul le propriétaire gère les utilisateurs, paramètres et rapports financiers."""

    def has_permission(self, request, view):
        user = request.user
        return bool(super().has_permission(request, view) and user.role == "owner")


class IsNotBlocked(permissions.BasePermission):
    message = "Votre compte a été bloqué. Contactez la boutique."

    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated and getattr(user, "is_blocked", False):
            raise PermissionDenied(self.message)
        return True


from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    message = "Super Admin access is required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "super_admin"
            and request.user.is_active
        )


class IsAdminOrSuperAdmin(BasePermission):
    message = "Administrator access is required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.role in ["super_admin", "admin"]
        )
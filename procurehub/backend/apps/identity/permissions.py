from rest_framework.permissions import BasePermission


def has_any_role(user, *roles):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.roles.filter(role_code__in=roles).exists()


class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN")


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, "MANAGER", "SYSTEM_ADMIN")


class IsFinance(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, "FINANCE")


class IsAuthenticatedCompanyMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

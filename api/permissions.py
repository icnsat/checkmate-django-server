# permissions.py
from rest_framework import permissions


class IsNotBlocked(permissions.BasePermission):
    message = 'Ваш аккаунт заблокирован. Бронирование недоступно.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and not request.user.is_blocked


class IsStaff(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class IsAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class IsAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return (
                    request.method in permissions.SAFE_METHODS
                    or (
                        request.user.is_authenticated
                        and request.user.is_superuser
                    )
                )


class IsStaffOwnerOrAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return (
                    request.method in permissions.SAFE_METHODS
                    or (
                        request.user.is_authenticated
                        and request.user.is_staff
                    )
                )

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.manager == request.user
            or request.user.is_superuser
        )


class OwnerOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return (
                request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated
            )

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsOwner(permissions.BasePermission):
    """
    Разрешение, которое позволяет доступ только владельцу объекта.
    """
    def has_object_permission(self, request, view, obj):
        # Разрешаем доступ только если пользователь является владельцем
        return obj == request.user


class IsOwnerOrAdminForBooking(permissions.BasePermission):
    """
    Пользователь может создавать и просматривать свои бронирования.
    Админ может просматривать и изменять статус всех.
    """

    def has_permission(self, request, view):
        # Любой аутентифицированный может создать или смотреть список (GET, POST)
        if request.method in ['POST', 'GET']:
            return request.user.is_authenticated

        # Изменения — только для админа
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        # Админ может делать всё
        if request.user.is_superuser:
            return True

        # Пользователь может просматривать только свои брони
        return (
            obj.user == request.user
            and request.method in permissions.SAFE_METHODS
        )

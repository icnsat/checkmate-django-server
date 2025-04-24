from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Country, City, Hotel, Room, Booking, Review, Discount


# Отображение первой старницы создания нового пользователя
# и полной страницы редактирования пользователя
class UserAdmin(BaseUserAdmin):
    # Отображение списка пользователей
    ordering = ['username']
    list_display = [
        'username',
        'email',
        'is_staff',
        'is_superuser',
        'is_blocked'
    ]

    # Все поля при редактировании пользователя
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password', 'is_blocked')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Все поля первой старницы создания пользователя
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    # Поля, по которым можно искать пользователей
    search_fields = ['email', 'username']


# Регистрируем модель с минимальной кастомизацией (только для User)
admin.site.register(User, UserAdmin)

# Стандартная регистрация остальных моделей
admin.site.register(Country)
admin.site.register(City)
admin.site.register(Hotel)
admin.site.register(Room)
admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(Discount)

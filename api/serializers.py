import base64
from rest_framework import serializers
from django.core.files.base import ContentFile
from djoser.serializers import (
    UserCreateSerializer as BaseUserCreateSerializer,
    UserSerializer as BaseUserSerializer
)
from .models import User, Hotel, Room, Booking, Review, Discount, Country, City


# Для регистрации нового пользователя
class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password')


# Для получения данных о пользователе
class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username')


class UserAdminSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'username',
            'is_blocked',
            'theme',
            'is_staff',
            'is_superuser'
        )
        read_only_fields = ('id', 'email', 'username', )


# Сериализатор для страны
class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('name',)
        # read_only_fields = ('id',)


# Сериализатор для города
class CitySerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = City
        fields = ('id', 'name', 'country')
        read_only_fields = ('id',)


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Если полученный объект строка, и эта строка
        # начинается с 'data:image'...
        if isinstance(data, str) and data.startswith('data:image'):
            # ...начинаем декодировать изображение из base64.
            # Сначала нужно разделить строку на части.
            format, imgstr = data.split(';base64,')  
            # И извлечь расширение файла.
            ext = format.split('/')[-1]
            # Затем декодировать сами данные и поместить результат в файл,
            # которому дать название по шаблону.
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


# Сериализатор для отеля
class HotelSerializer(serializers.ModelSerializer):
    city = serializers.SlugRelatedField(
        queryset=City.objects.all(),
        slug_field='name',  # Связь по названию города
        help_text="Название города (например, 'Санкт-Петербург')",
        error_messages={
            'does_not_exist': 'Город "{value}" не найден в базе. '
            'Проверьте название или создайте город.'
        }
    )
    image = Base64ImageField()  # required=False, allow_null=True)

    class Meta:
        model = Hotel
        fields = ('id', 'name', 'city', 'address', 'description', 'image', 'rating')
        read_only_fields = ('id', 'rating')  # Эти поля нельзя изменять напрямую

    def to_representation(self, instance):
        """При GET-запросе отображаем город как объект с деталями"""
        data = super().to_representation(instance)
        data['city'] = {
            # 'id': instance.city.id,
            'name': instance.city.name,
            'country': instance.city.country.name  # Если нужно включить страну
        }
        return data


# Сериализатор для номера отеля
class RoomSerializer(serializers.ModelSerializer):
    hotel = serializers.SlugRelatedField(
        queryset=Hotel.objects.all(),
        slug_field='name',  # Связь по названию города
        help_text="Название Отеля",
        error_messages={
            'does_not_exist': 'Отель "{value}" не найден в базе. '
            'Проверьте название или создайте отель.'
        }
    )
    image = Base64ImageField()

    class Meta:
        model = Room
        fields = ('id', 'hotel', 'room_type', 'capacity',
                  'price', 'description', 'image')
        read_only_fields = ('id',)  # Эти поля нельзя изменять напрямую


class RoomShortSerializer(serializers.ModelSerializer):
    hotel = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'hotel']


# для чтения
class BookingSerializer(serializers.ModelSerializer):
    # room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    room = RoomShortSerializer(read_only=True)

    # total_price = serializers.SerializerMethodField()

    email = serializers.SerializerMethodField()

    has_review = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'room',
            'start_date',
            'end_date',
            'guests',
            'first_name',
            'last_name',
            'email',
            'phone',
            'discount_applied',
            'total_price',
            'status',
            'created_at',
            'has_review',
        ]
        read_only_fields = ['created_at']

    # Поле email не хранится в модели, берется из связанного пользователя
    def get_email(self, obj):
        return obj.user.email if obj.user else None

    # def get_total_price(self, obj):
    #     return obj.total_price

    def get_has_review(self, obj):
        return hasattr(obj, 'review')


# для создания бронирования
class BookingCreateSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    discount_applied = serializers.BooleanField(read_only=True)

    total_price = serializers.SerializerMethodField()

    email = serializers.SerializerMethodField()

    # Поле email не хранится в модели, берется из связанного пользователя
    def get_email(self, obj):
        return obj.user.email if obj.user else None

    def get_total_price(self, obj):
        return obj.total_price

    class Meta:
        model = Booking
        fields = [
            'id',
            'room',
            'start_date',
            'end_date',
            'guests',
            'first_name',
            'last_name',
            'email',
            'phone',
            'discount_applied',
            'total_price',
            'status',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def validate(self, data):
        request = self.context.get('request')

        if self.partial and request and request.method == 'PATCH':
            # Разрешить только админам менять только статус
            if not request.user.is_superuser:
                raise serializers.ValidationError("Изменение возможно только для администратора.")

            if set(self.initial_data.keys()) != {"status"}:
                raise serializers.ValidationError("Можно изменить только статус бронирования.")

            return data

        #  Пример базовой валидации (не наезжают ли даты друг на друга)
        room = data['room']
        start = data['start_date']
        end = data['end_date']

        if start >= end:
            raise serializers.ValidationError(
                "Дата заезда должна быть раньше даты выезда."
            )

        overlapping = Booking.objects.filter(
            room=room,
            start_date__lt=end,
            end_date__gt=start
        ).exists()

        if overlapping:
            raise serializers.ValidationError("Комната занята на выбранные даты.")

        return data


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)
    hotel = serializers.SerializerMethodField(read_only=True)

    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())

    class Meta:
        model = Review
        fields = [
            'id',
            'booking',
            'user',
            'hotel',
            'text',
            'rating',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['user', 'hotel', 'created_at', 'updated_at']

    def get_user(self, obj):
        return obj.booking.user.username

    def get_hotel(self, obj):
        return obj.booking.room.hotel.name

    def validate(self, data):
        # Получаем бронирование
        booking = data.get('booking')

        # Получаем текущего пользователя из контекста
        user = self.context['request'].user

        # Проверка: бронирование должно принадлежать текущему пользователю
        if booking.user != user:
            raise serializers.ValidationError("Вы не можете оставить отзыв на чужое бронирование.")

        # Проверка: отзыв можно оставить только для подтвержденных бронирований
        if booking.status != 'confirmed':
            raise serializers.ValidationError("Нельзя оставить отзыв по неподтвержденному бронированию.")

        # Проверка: отзыв можно оставить только один раз
        if hasattr(booking, 'review'):
            raise serializers.ValidationError("На это бронирование уже был оставлен отзыв.")

        return data

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Рейтинг должен быть от 1 до 5.")
        return value


# Сериализатор для скидки
class DiscountSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Discount
        fields = ('id', 'user', 'amount', 'expires_at', 'used')

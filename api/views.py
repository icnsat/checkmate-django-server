from rest_framework import viewsets, permissions, status, views
from rest_framework.generics import ListAPIView
from .models import (
    Hotel,
    Room,
    City,
    Booking,
    Review,
    Discount,
    User
)
from .serializers import (
    HotelSerializer,
    RoomSerializer,
    CitySerializer,
    BookingSerializer,
    ReviewSerializer,
    UserAdminSerializer,
)
from rest_framework.response import Response
from .permissions import (
    IsNotBlocked,
    IsStaff,
    IsAdmin,
    IsStaffOwnerOrAdminOrReadOnly,
    OwnerOrReadOnly,
    IsAdminOrReadOnly,
    IsOwnerOrAdminForBooking,
    IsOwner
)
from django.utils import timezone
from random import randint
from datetime import timedelta
from django.urls import reverse
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend


# class HotelViewSet(viewsets.ReadOnlyModelViewSet):
class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.select_related('city', 'city__country').all()
    serializer_class = HotelSerializer
    permission_classes = [IsStaffOwnerOrAdminOrReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('city__name',)

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)


# class RoomViewSet(viewsets.ReadOnlyModelViewSet):
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.select_related('hotel', 'hotel__city').all()
    serializer_class = RoomSerializer
    permission_classes = [IsStaffOwnerOrAdminOrReadOnly]

    def get_queryset(self):
        hotel_id = self.kwargs['hotel_pk']
        return Room.objects.filter(hotel__id=hotel_id)


class CityListView(ListAPIView):
    queryset = City.objects.select_related('country').all()
    serializer_class = CitySerializer


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBlocked,
        IsOwnerOrAdminForBooking
    ]

    def get_queryset(self):
        user = self.request.user
        # Админ видит всё
        if user.is_superuser:
            return Booking.objects.all()
        # Пользователь — только свои брони
        return Booking.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        room = serializer.validated_data['room']
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']

        days = (end_date - start_date).days
        base_price = room.price * days

        # Попробуем найти активную скидку
        discount = Discount.objects.filter(
            user=user,
            used=False,
            expires_at__gt=timezone.now()
        ).first()

        discount_amount = 0
        discount_applied = False
        if discount:
            discount_amount = base_price * (Decimal(discount.amount) / 100)
            base_price -= discount_amount
            discount_applied = True
            discount.used = True
            discount.save()

        serializer.save(
            user=user,
            status='pending',
            created_at=timezone.now(),
            total_price=base_price,
            discount_applied=discount_applied,
        )

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Только админ может изменять бронирования.")

        partial = kwargs.get('partial', False)  # Важно: передаём partial в сериализатор

        instance = self.get_object()
        data = request.data

        # Проверяем, что можно менять только статус
        if 'status' not in data or len(data) > 1:
            raise PermissionDenied("Админ может изменить только поле 'status'.")

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [OwnerOrReadOnly]

    def get_queryset(self):
        hotel_id = self.kwargs['hotel_pk']
        return Review.objects.filter(booking__room__hotel__id=hotel_id)

    def perform_create(self, serializer):
        # Присваиваем пользователю при создании
        # serializer.save(user=self.request.user)

        serializer.save()


class RouletteView(views.APIView):
    """Рулетка для случайной скидки."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Выбор случайной скидки."""

        # Параметры скидки
        discount_amount = randint(5, 30)  # Скидка от 5 до 30 процентов
        expires_at = timezone.now() + timedelta(days=1)  # Срок действия скидки — 1 день

        # Проверка, что у пользователя еще нет активной скидки
        if Discount.objects.filter(
            user=request.user,
            used=False,
            expires_at__gt=timezone.now()
        ).exists():
            return Response(
                {"detail": "У вас уже есть активная скидка."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Создаем скидку
        discount = Discount.objects.create(
            user=request.user,
            amount=discount_amount,
            expires_at=expires_at
        )

        return Response(
            {"discount_code": discount.id,
             "discount_amount": discount.amount,
             "expires_at": discount.expires_at},
            status=status.HTTP_200_OK
        )


class UserAdminViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserAdminSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_permissions(self):
        # Переопределяем метод get_permissions для разных действий
        if self.action == 'toggle_theme':
            return [permissions.IsAuthenticated(), IsOwner()]
        return super().get_permissions()

    # @action(detail=True, methods=['post'])
    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = not user.is_blocked
        user.save()
        return Response(
            {
                "user": user.username,
                "active": not user.is_blocked,
                "status": (
                    "User activated"
                    if not user.is_blocked
                    else "User blocked"
                )
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def toggle_theme(self, request, pk=None):
        user = self.get_object()
        user.theme = (
            "light"
            if user.theme == "dark"
            else "dark"
        )
        user.save()
        return Response(
            {
                "user": user.username,
                "theme": user.theme
            },
            status=status.HTTP_200_OK
        )


class APIRootView(views.APIView):
    """Отображает все доступные эндпоинты API."""
    def get(self, request):
        base_url = request.build_absolute_uri('/')

        # routes = {
        #     'hotels': request.build_absolute_uri(reverse('hotel-list')),
        #     'rooms': request.build_absolute_uri(reverse('room-list')),
        #     'bookings': request.build_absolute_uri(reverse('booking-list')),
        #     'reviews': request.build_absolute_uri(reverse('review-list')),
        #     'cities': request.build_absolute_uri(reverse('city-list')),
        #     'discounts_roulette': request.build_absolute_uri(
        #         reverse('roulette-discount')
        #     ),

        routes = {
            "Authentication": {
                "login": f"{base_url}auth/jwt/create/",
                "register": f"{base_url}auth/users/",
            },
            "Hotels": {
                "list": f"{base_url}hotels/",
                "detail": f"{base_url}hotels/1/",
            },
            "Rooms": {
                "list": f"{base_url}hotels/1/rooms/",
                "detail": f"{base_url}hotels/1/rooms/1/",
            },
            "Users": {
                "list": f"{base_url}users/",
                "detail": f"{base_url}users/1/",
                "block": f"{base_url}users/1/toggle_active/",
            },
            "Bookings": {
                "list": f"{base_url}bookings/",
                "detail": f"{base_url}bookings/1/",
            },
            "Reviews": {
                "list": f"{base_url}hotels/1/reviews/",
                "detail": f"{base_url}hotels/1/reviews/1/",
            },
            "Cities": {
                "list": f"{base_url}cities/",
            },
            "Discounts": {
                "detail": f"{base_url}discounts/roulette/",
            }
        }

        return Response(routes)

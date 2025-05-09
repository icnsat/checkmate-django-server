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
    BookingCreateSerializer,
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
from datetime import timedelta, datetime
from django.urls import reverse
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import OuterRef, Exists, Q


# class HotelViewSet(viewsets.ReadOnlyModelViewSet):
class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.select_related('city', 'city__country').all()
    serializer_class = HotelSerializer
    permission_classes = [IsStaffOwnerOrAdminOrReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('city__name',)

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)


class SearchHotelsView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        city_id = request.query_params.get('city_id')
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        guests = request.query_params.get('guests')

        if not all([city_id, check_in, check_out, guests]):
            return Response(
                {"error": "Missing required parameters"},
                status=400
            )

        try:
            check_in = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out, "%Y-%m-%d").date()
            guests = int(guests)
        except ValueError:
            return Response(
                {"error": "Invalid date or guests format"},
                status=400
            )

        if check_in >= check_out:
            return Response(
                {"error": "Check-in must be before check-out"},
                status=400
            )

        # Комнаты, у которых нет пересекающихся бронирований
        overlapping_bookings = Booking.objects.filter(
            room=OuterRef('pk'),
            start_date__lt=check_out,
            end_date__gt=check_in
        )

        available_rooms = Room.objects.annotate(
            is_booked=Exists(overlapping_bookings)
        ).filter(
            is_booked=False,
            capacity__gte=guests
        )

        hotels = Hotel.objects.filter(
            city__id__iexact=city_id,
            rooms__in=available_rooms
        ).distinct()

        serializer = HotelSerializer(hotels, many=True)
        return Response(serializer.data)


# class SearchRoomsView(views.APIView):
#     permission_classes = [permissions.AllowAny]

#     def get(self, request, hotel_id):
#         check_in = request.query_params.get('check_in')
#         check_out = request.query_params.get('check_out')
#         guests = request.query_params.get('guests')

#         if not all([check_in, check_out, guests]):
#             return Response(
#                 {"error": "Missing required parameters"},
#                 status=400
#             )

#         try:
#             check_in = datetime.strptime(check_in, "%Y-%m-%d").date()
#             check_out = datetime.strptime(check_out, "%Y-%m-%d").date()
#             guests = int(guests)
#         except ValueError:
#             return Response(
#                 {"error": "Invalid date or guests format"},
#                 status=400
#             )

#         if check_in >= check_out:
#             return Response(
#                 {"error": "Check-in must be before check-out"},
#                 status=400
#             )

#         overlapping_bookings = Booking.objects.filter(
#             room=OuterRef('pk'),
#             start_date__lt=check_out,
#             end_date__gt=check_in
#         )

#         available_rooms = Room.objects.annotate(
#             is_booked=Exists(overlapping_bookings)
#         ).filter(
#             is_booked=False,
#             capacity__gte=guests,
#             hotel_id=hotel_id  # фильтрация по отелю
#         )

#         serializer = RoomSerializer(available_rooms, many=True)
#         return Response(serializer.data)


# class RoomViewSet(viewsets.ReadOnlyModelViewSet):
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.select_related('hotel', 'hotel__city').all()
    serializer_class = RoomSerializer
    permission_classes = [IsStaffOwnerOrAdminOrReadOnly]

    def get_queryset(self):
        hotel_id = self.kwargs['hotel_pk']
        queryset = Room.objects.filter(hotel__id=hotel_id)

        # Читаем параметры запроса
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        guests = self.request.query_params.get('guests')

        # Если параметры не переданы — вернем просто все комнаты отеля
        if not all([check_in, check_out, guests]):
            return queryset

        # Если параметры есть — фильтруем
        try:
            check_in = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out, "%Y-%m-%d").date()
            guests = int(guests)
        except ValueError:
            return queryset.none()

        if check_in >= check_out:
            return queryset.none()

        overlapping_bookings = Booking.objects.filter(
            room=OuterRef('pk'),
            start_date__lt=check_out,
            end_date__gt=check_in
        )

        queryset = queryset.annotate(
            is_booked=Exists(overlapping_bookings)
        ).filter(
            is_booked=False,
            capacity__gte=guests
        )

        return queryset


class CityListView(ListAPIView):
    queryset = City.objects.select_related('country').all()
    serializer_class = CitySerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name', "country__name")


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()

    # permission_classes = [
    #     permissions.IsAuthenticated,
    #     IsNotBlocked,
    #     IsOwnerOrAdminForBooking
    # ]

    def get_permission_classes(self):
        if self.action == 'get':
            return [permissions.IsAuthenticated, IsOwnerOrAdminForBooking]
        else:
            return [permissions.IsAuthenticated,
                    IsNotBlocked,
                    IsOwnerOrAdminForBooking]
    # serializer_class = BookingSerializer

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BookingCreateSerializer
        return BookingSerializer

    def get_queryset(self):
        user = self.request.user

        # Return empty queryset for anonymous users
        if not user.is_authenticated:
            return Booking.objects.none()

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
        """Проверка наличия активной скидки без создания новой."""
        existing_discount = Discount.objects.filter(
            user=request.user,
            used=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_discount:
            return Response(
                {
                    "detail": "У вас уже есть активная скидка: ",
                    "discount_code": existing_discount.id,
                    "discount_amount": existing_discount.amount,
                    "expires_at": existing_discount.expires_at
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "У вас нет активной скидки."},
            status=status.HTTP_204_NO_CONTENT
        )

    def post(self, request, *args, **kwargs):
        """Создание новой скидки (если нет активной)."""
        existing_discount = Discount.objects.filter(
            user=request.user,
            used=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_discount:
            return Response(
                {"detail": "У вас уже есть активная скидка: ",
                 "discount_code": existing_discount.id,
                 "discount_amount": existing_discount.amount,
                 "expires_at": existing_discount.expires_at
                 },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Параметры новой скидки
        discount_amount = randint(5, 30)  # Скидка от 5 до 30 процентов
        expires_at = timezone.now() + timedelta(days=1)  # Срок действия скидки — 1 день

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
            status=status.HTTP_201_CREATED
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

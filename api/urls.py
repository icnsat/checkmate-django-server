from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    HotelViewSet,
    SearchHotelsView,
    RoomViewSet,
    CityListView,
    BookingViewSet,
    ReviewViewSet,
    RouletteView,
    APIRootView,
    UserAdminViewSet,
)

router = DefaultRouter()
router.register(r'hotels', HotelViewSet, basename='hotel')
# router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'bookings', BookingViewSet, basename='booking')
# router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'users', UserAdminViewSet, basename='user')

# Вложенные роутеры для номеров и отзывов
hotel_router = routers.NestedDefaultRouter(router, r'hotels', lookup='hotel')
hotel_router.register(r'rooms', RoomViewSet, basename='hotel-rooms')
hotel_router.register(r'reviews', ReviewViewSet, basename='hotel-reviews')

urlpatterns = [
    path('', APIRootView.as_view()),
    path('', include(router.urls)),  # ViewSet'ы
    path('', include(hotel_router.urls)),  # Вложенные роутеры

    path('cities/', CityListView.as_view(), name='city-list'),
    path(
        'search/',
        SearchHotelsView.as_view(),
        name='search-hotels'
    ),
    # path('hotels/', views.HotelListView.as_view(), name='hotel-list'),
    # path('hotels/<int:pk>/', views.HotelDetailView.as_view(), name='hotel-detail'),
    # path('hotels/<int:hotel_id>/rooms/', views.RoomListView.as_view(), name='room-list'),
    # path('rooms/<int:pk>/', views.RoomDetailView.as_view(), name='room-detail'),
    # path('bookings/', views.BookingCreateView.as_view(), name='booking-create'),
    # path('bookings/user/', views.UserBookingsView.as_view(), name='user-bookings'),
    # path('reviews/', views.ReviewCreateView.as_view(), name='review-create'),
    # path('discounts/', views.DiscountView.as_view(), name='discount-list'),
    # path('theme/', views.ThemeUpdateView.as_view(), name='theme-update'),
    path(
        'discounts/roulette/',
        RouletteView.as_view(),
        name='roulette-discount'
    ),
]

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


# Пользователь
# Добавляем/редактируем поля в AbstractUser 
class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_blocked = models.BooleanField(default=False)
    theme = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        # return self.email
        return self.username


# Страна и город
class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}, {self.country.name}"


# Отель
class Hotel(models.Model):
    name = models.CharField(max_length=255)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='hotels/')
    rating = models.FloatField(default=0.0)

    manager = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name='managed_hotels'
        )

    def __str__(self):
        return self.name

    def update_rating(self):
        # reviews = self.reviews.all()

        reviews = Review.objects.filter(booking__room__hotel=self)

        # if reviews.exists():

        avg_rating = reviews.aggregate(
            models.Avg('rating')
        )['rating__avg'] or 0

        self.rating = round(avg_rating, 2)
        self.save()


# Номер в отеле
class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='rooms/')

    def __str__(self):
        return f"{self.hotel.name} - {self.room_type}"


# Скидка от рулетки
class Discount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()  # Процент
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()

    def __str__(self):
        return (
            f"{self.user.username}: {self.amount}% "
            f"({'ended' if (self.used or not self.is_valid()) else 'works'})"
        )


# Бронирование
class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('confirmed', 'Подтверждено'),
        ('canceled', 'Отменено'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    guests = models.PositiveIntegerField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    # email = models.CharField(max_length=30)
    phone = models.CharField(max_length=30)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_applied = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.room.hotel.name} ({self.status})"


# Отзыв о отеле
class Review(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    # hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='reviews')

    # text = models.TextField()
    # rating = models.PositiveSmallIntegerField(
    #     default=1,
    #     choices=[(i, i) for i in range(1, 6)]
    # )
    # created_at = models.DateTimeField(auto_now_add=True)

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     self.hotel.update_rating()

    # def __str__(self):
    #     return f"{self.user.email} - {self.hotel.name} ({self.rating})"

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='review'
    )
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(
        default=1,
        choices=[(i, i) for i in range(1, 6)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.booking.status != 'confirmed':
            raise ValidationError(
                "Отзыв можно оставить только по подтвержденному бронированию."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.booking.room.hotel.update_rating()

    def __str__(self):
        return (
            f"{self.booking.user.email} - {self.booking.room.hotel.name} "
            f"({self.rating})"
        )

    @property
    def user(self):
        return self.booking.user

    @property
    def hotel(self):
        return self.booking.room.hotel

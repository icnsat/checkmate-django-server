from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Добавляем только нужные поля в токен
        if (user.is_superuser):
            token['role'] = 'admin'
        elif (user.is_staff):
            token['role'] = 'staff'
        else:
            token['role'] = 'user'
        token['username'] = user.username  # Опционально
        return token

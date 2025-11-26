from account.models import CustomUser
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "email", "full_name", "role", "is_active", "is_staff", "is_superuser", "last_login", "date_joined"]
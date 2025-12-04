from rest_framework_simplejwt.views import TokenObtainPairView

from account.token_serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Token obtain view that uses CustomTokenObtainPairSerializer to include
    role and name in the token payload and login response.
    """

    serializer_class = CustomTokenObtainPairSerializer



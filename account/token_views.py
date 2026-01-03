from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle

from account.token_serializers import CustomTokenObtainPairSerializer


class LoginThrottle(AnonRateThrottle):
    """Custom throttle for login endpoint - 5 requests per minute."""
    rate = '5/minute'


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Token obtain view that uses CustomTokenObtainPairSerializer to include
    role and name in the token payload and login response.
    Includes rate limiting to prevent brute force attacks.
    """

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]



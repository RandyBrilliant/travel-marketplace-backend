from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from account.models import UserRole


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extend the default SimpleJWT serializer to embed extra user info
    into both:
    - the JWT payload (so backend can read it from request.user if using custom user claims)
    - the login response body (so frontend can easily access without decoding)
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Basic role and email are always safe to expose
        token["role"] = user.role
        token["email"] = user.email

        # Determine a display name depending on role/profile
        display_name = None
        try:
            if user.role == UserRole.SUPPLIER and hasattr(user, "supplier_profile"):
                display_name = user.supplier_profile.company_name
            elif user.role == UserRole.RESELLER and hasattr(user, "reseller_profile"):
                display_name = user.reseller_profile.display_name
            elif user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
                display_name = user.staff_profile.name
            elif user.role == UserRole.CUSTOMER and hasattr(user, "customer_profile"):
                display_name = user.customer_profile.full_name
        except Exception:
            # If anything goes wrong, just skip display_name to avoid breaking auth
            display_name = None

        if display_name:
            token["name"] = display_name

        return token

    def validate(self, attrs):
        """
        Add the same extra fields into the serialized response body so the
        frontend can read them without decoding the JWT.
        """
        data = super().validate(attrs)

        user = self.user
        data["role"] = user.role

        # Default name to email if we cannot resolve a nicer display name
        name = None
        try:
            if user.role == UserRole.SUPPLIER and hasattr(user, "supplier_profile"):
                name = user.supplier_profile.company_name
            elif user.role == UserRole.RESELLER and hasattr(user, "reseller_profile"):
                name = user.reseller_profile.display_name
            elif user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
                name = user.staff_profile.name
            elif user.role == UserRole.CUSTOMER and hasattr(user, "customer_profile"):
                name = user.customer_profile.full_name
        except Exception:
            name = None

        data["name"] = name or user.email

        return data



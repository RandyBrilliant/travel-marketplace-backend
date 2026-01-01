from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import secrets
import string

from account.models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    UserRole,
)


def generate_unique_referral_code(length=8):
    """
    Generate a unique referral code for resellers.
    Uses uppercase letters and numbers.
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(characters) for _ in range(length))
        if not ResellerProfile.objects.filter(referral_code=code).exists():
            return code


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "role",
            "email_verified",
            "email_verified_at",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "date_joined",
        ]
        read_only_fields = [
            "is_staff",
            "is_superuser",
            "email_verified",
            "email_verified_at",
            "last_login",
            "date_joined",
        ]


class SupplierProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SupplierProfile
        fields = [
            "id",
            "user",
            "company_name",
            "contact_person",
            "contact_phone",
            "address",
            "tax_id",
            "photo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class ResellerProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    sponsor = serializers.PrimaryKeyRelatedField(
        queryset=ResellerProfile.objects.all(),
        required=False,
        allow_null=True,
    )
    sponsor_referral_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Referral code of the sponsor (if joining under someone).",
    )

    class Meta:
        model = ResellerProfile
        fields = [
            "id",
            "user",
            "full_name",
            "contact_phone",
            "address",
            "referral_code",
            "sponsor",
            "sponsor_referral_code",
            "group_root",
            "commission_rate",
            "upline_commission_rate",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "direct_downline_count",
            "photo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "group_root",
            "direct_downline_count",
            "created_at",
            "updated_at",
        ]

    def validate_sponsor_referral_code(self, value):
        """Validate that sponsor referral code exists if provided."""
        if value:
            try:
                ResellerProfile.objects.get(referral_code=value)
            except ResellerProfile.DoesNotExist:
                raise serializers.ValidationError(
                    f"Sponsor with referral code '{value}' does not exist."
                )
        return value


class StaffProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            "id",
            "user",
            "full_name",
            "contact_phone",
            "photo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


# ==================== ADMIN SERIALIZERS ====================
# Admin serializers that allow setting the user field and include nested user data


class BaseAdminProfileSerializer(serializers.ModelSerializer):
    """Base admin serializer with common functionality for all profile types."""
    
    user_data = UserSerializer(source="user", read_only=True)
    
    # User creation fields (for auto-creating user when creating profile)
    email = serializers.EmailField(write_only=True, required=False)
    password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    
    def validate(self, attrs):
        """Validate that if creating new user, email and password are provided."""
        email = attrs.get("email")
        password = attrs.get("password")
        user = attrs.get("user")
        
        # If user is not provided, email and password are required
        if not user:
            if email and not password:
                raise serializers.ValidationError(
                    {"password": "Password is required when creating a new user."}
                )
            if password and not email:
                raise serializers.ValidationError(
                    {"email": "Email is required when creating a new user."}
                )
        
        return attrs


class AdminSupplierProfileSerializer(BaseAdminProfileSerializer, SupplierProfileSerializer):
    """Admin serializer that allows setting the user field and includes nested user data."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role=UserRole.SUPPLIER),
        required=False,
        allow_null=True,
    )

    class Meta(SupplierProfileSerializer.Meta):
        fields = SupplierProfileSerializer.Meta.fields + ["user_data", "email", "password"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminResellerProfileSerializer(BaseAdminProfileSerializer, ResellerProfileSerializer):
    """Admin serializer that allows setting the user field and includes nested user data."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role=UserRole.RESELLER),
        required=False,
        allow_null=True,
    )

    class Meta(ResellerProfileSerializer.Meta):
        fields = ResellerProfileSerializer.Meta.fields + ["user_data", "email", "password"]
        read_only_fields = [
            "id",
            "group_root",
            "direct_downline_count",
            "created_at",
            "updated_at",
        ]


class AdminStaffProfileSerializer(BaseAdminProfileSerializer, StaffProfileSerializer):
    """Admin serializer that allows setting the user field and includes nested user data."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role=UserRole.STAFF),
        required=False,
        allow_null=True,
    )

    class Meta(StaffProfileSerializer.Meta):
        fields = StaffProfileSerializer.Meta.fields + ["user_data", "email", "password"]
        read_only_fields = ["id", "created_at", "updated_at"]


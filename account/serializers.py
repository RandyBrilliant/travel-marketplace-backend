from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
import secrets
import string

from account.models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    UserRole,
)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change requests."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        """Validate the new password meets requirements."""
        validate_password(value)
        return value

    def validate(self, attrs):
        """Validate that old and new passwords are different."""
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': ['New password must be different from old password.']
            })
        return attrs


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
    email = serializers.EmailField(source="user.email", read_only=True)
    email_verified = serializers.BooleanField(source="user.email_verified", read_only=True)

    class Meta:
        model = SupplierProfile
        fields = [
            "id",
            "user",
            "company_name",
            "contact_person",
            "contact_phone",
            "address",
            "photo",
            "email",
            "email_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "email", "email_verified", "created_at", "updated_at"]


class ResellerProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    sponsor = serializers.PrimaryKeyRelatedField(
        queryset=ResellerProfile.objects.all(),
        required=False,
        allow_null=True,
    )
    sponsor_name = serializers.CharField(source="sponsor.full_name", read_only=True)
    sponsor_referral_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Referral code of the sponsor (if joining under someone).",
    )
    group_root_name = serializers.CharField(source="group_root.full_name", read_only=True, allow_null=True)

    class Meta:
        model = ResellerProfile
        fields = [
            "id",
            "user",
            "email",
            "full_name",
            "contact_phone",
            "address",
            "referral_code",
            "sponsor",
            "sponsor_name",
            "sponsor_referral_code",
            "group_root",
            "group_root_name",
            "base_commission",
            "upline_commission_amount",
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
            "email",
            "referral_code",
            "group_root",
            "group_root_name",
            "direct_downline_count",
            "created_at",
            "updated_at",
        ]

    def validate_base_commission(self, value):
        """Validate base commission is non-negative."""
        if value < 0:
            raise serializers.ValidationError(
                "Base commission must be greater than or equal to 0."
            )
        return value

    def validate_upline_commission_amount(self, value):
        """Validate upline commission amount is non-negative."""
        if value < 0:
            raise serializers.ValidationError(
                "Upline commission amount must be greater than or equal to 0."
            )
        return value

    def validate_sponsor_referral_code(self, value):
        """Validate that sponsor referral code exists if provided."""
        if value:
            # Normalize referral code: uppercase and strip whitespace
            # Referral codes are uppercase by default, so normalize for consistency
            normalized_code = value.upper().strip()
            try:
                ResellerProfile.objects.get(referral_code=normalized_code)
            except ResellerProfile.DoesNotExist:
                raise serializers.ValidationError(
                    f"Sponsor with referral code '{normalized_code}' does not exist."
                )
            return normalized_code
        return value

    def _validate_no_circular_sponsor(self, sponsor, current_instance=None):
        """
        Validate that setting this sponsor won't create a circular relationship.
        A circular relationship occurs if the sponsor is in the current reseller's downline.
        """
        if not sponsor or not current_instance:
            return
        
        # Check for self-sponsorship
        if sponsor.pk == current_instance.pk:
            raise serializers.ValidationError(
                {"sponsor": "A reseller cannot be their own sponsor."}
            )
        
        # Check if sponsor is in the current reseller's downline (would create a circle)
        if current_instance.pk:
            # Get all downlines of the current reseller using group_root
            downlines = current_instance.all_downlines()
            if sponsor in downlines:
                raise serializers.ValidationError(
                    {"sponsor": f"Cannot set sponsor: {sponsor.full_name} is in your downline. This would create a circular relationship."}
                )

    def create(self, validated_data):
        """Create reseller profile and automatically generate referral code."""
        # Handle sponsor_referral_code lookup
        sponsor_referral_code = validated_data.pop("sponsor_referral_code", None)
        sponsor = validated_data.get("sponsor")
        
        if sponsor_referral_code:
            # Normalize referral code for lookup (uppercase and strip whitespace)
            normalized_code = sponsor_referral_code.upper().strip()
            try:
                sponsor = ResellerProfile.objects.get(referral_code=normalized_code)
                validated_data["sponsor"] = sponsor
            except ResellerProfile.DoesNotExist:
                raise serializers.ValidationError(
                    {"sponsor_referral_code": f"Sponsor with referral code '{normalized_code}' does not exist."}
                )
        
        # Generate referral code if not provided
        referral_code = validated_data.get("referral_code")
        if not referral_code:
            validated_data["referral_code"] = generate_unique_referral_code()
        
        # Create instance (group_root will be set by model's save method)
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        """Update reseller profile and handle sponsor_referral_code lookup."""
        # Handle sponsor_referral_code lookup
        sponsor_referral_code = validated_data.pop("sponsor_referral_code", None)
        sponsor = validated_data.get("sponsor")
        
        if sponsor_referral_code:
            # Normalize referral code for lookup (uppercase and strip whitespace)
            normalized_code = sponsor_referral_code.upper().strip()
            try:
                sponsor = ResellerProfile.objects.get(referral_code=normalized_code)
                validated_data["sponsor"] = sponsor
            except ResellerProfile.DoesNotExist:
                raise serializers.ValidationError(
                    {"sponsor_referral_code": f"Sponsor with referral code '{normalized_code}' does not exist."}
                )
        
        # Validate sponsor if it's being set or changed
        if sponsor is not None:
            # Prevent circular relationships
            self._validate_no_circular_sponsor(sponsor, instance)
        
        return super().update(instance, validated_data)


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
    # User update fields (for updating user properties)
    # Note: is_active is handled by a separate activate/deactivate endpoint
    
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
            "user",
            "referral_code",  # Auto-generated, should be read-only
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


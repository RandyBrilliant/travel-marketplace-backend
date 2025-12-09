from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
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
            "phone_number",
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
            "status",
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
            "display_name",
            "contact_phone",
            "address",
            "referral_code",
            "sponsor",
            "sponsor_referral_code",
            "group_root",
            "own_commission_rate",
            "upline_commission_rate",
            "status",
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
            "name",
            "job_title",
            "department",
            "contact_phone",
            "photo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Allows creating a new user account with optional profile creation.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
        help_text="Password must meet Django's password validation requirements.",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Enter the same password as above, for verification.",
    )

    # Optional profile data nested in registration
    supplier_profile = SupplierProfileSerializer(required=False, write_only=True)
    reseller_profile = ResellerProfileSerializer(required=False, write_only=True)
    staff_profile = StaffProfileSerializer(required=False, write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "phone_number",
            "password",
            "password_confirm",
            "role",
            "supplier_profile",
            "reseller_profile",
            "staff_profile",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "role": {"required": True},
            "phone_number": {"required": False},
        }

    def validate(self, attrs):
        """
        Validate that password and password_confirm match.
        Also validate that profile data matches the selected role.
        """
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "Password fields didn't match."}
            )

        role = attrs.get("role")
        supplier_profile = attrs.get("supplier_profile")
        reseller_profile = attrs.get("reseller_profile")
        staff_profile = attrs.get("staff_profile")

        # Validate that profile data matches the role
        if role == UserRole.SUPPLIER:
            if reseller_profile or staff_profile:
                raise serializers.ValidationError(
                    "Cannot provide reseller_profile or staff_profile when role is SUPPLIER."
                )
        elif role == UserRole.RESELLER:
            if supplier_profile or staff_profile:
                raise serializers.ValidationError(
                    "Cannot provide supplier_profile or staff_profile when role is RESELLER."
                )
        elif role == UserRole.STAFF:
            if supplier_profile or reseller_profile:
                raise serializers.ValidationError(
                    "Cannot provide supplier_profile or reseller_profile when role is STAFF."
                )

        return attrs

    def validate_role(self, value):
        """
        Optionally restrict STAFF registration to admin-only.
        For now, allow all roles to be registered publicly.
        """
        # Uncomment below if you want to restrict STAFF registration:
        # if value == UserRole.STAFF:
        #     raise serializers.ValidationError(
        #         "STAFF role registration is not allowed. Please contact an administrator."
        #     )
        return value

    def create(self, validated_data):
        """
        Create the user and optionally create the associated profile.
        """
        # Extract profile data (if any)
        supplier_profile_data = validated_data.pop("supplier_profile", None)
        reseller_profile_data = validated_data.pop("reseller_profile", None)
        staff_profile_data = validated_data.pop("staff_profile", None)

        # Extract phone_number if provided
        phone_number = validated_data.pop("phone_number", None)

        # Remove password_confirm (not needed for user creation)
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")

        # Create the user
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            password=password,
            role=validated_data.get("role", UserRole.RESELLER),
        )
        
        # Set phone_number if provided
        if phone_number:
            user.phone_number = phone_number
            user.save()

        # Create profile based on role
        if user.role == UserRole.SUPPLIER and supplier_profile_data:
            SupplierProfile.objects.create(user=user, **supplier_profile_data)
        elif user.role == UserRole.RESELLER and reseller_profile_data:
            # Handle reseller profile creation with referral code and sponsor
            sponsor_referral_code = reseller_profile_data.pop("sponsor_referral_code", None)
            
            # Generate referral_code if not provided
            if "referral_code" not in reseller_profile_data or not reseller_profile_data.get("referral_code"):
                reseller_profile_data["referral_code"] = generate_unique_referral_code()
            
            # Look up sponsor by referral code if provided
            sponsor = None
            if sponsor_referral_code:
                try:
                    sponsor = ResellerProfile.objects.get(referral_code=sponsor_referral_code)
                    reseller_profile_data["sponsor"] = sponsor
                except ResellerProfile.DoesNotExist:
                    # This should not happen due to validation, but handle gracefully
                    pass
            
            ResellerProfile.objects.create(user=user, **reseller_profile_data)
        elif user.role == UserRole.STAFF and staff_profile_data:
            StaffProfile.objects.create(user=user, **staff_profile_data)

        return user


# ==================== ADMIN SERIALIZERS ====================
# Admin serializers that allow setting the user field


class AdminSupplierProfileSerializer(SupplierProfileSerializer):
    """Admin serializer that allows setting the user field."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role=UserRole.SUPPLIER)
    )

    class Meta(SupplierProfileSerializer.Meta):
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminResellerProfileSerializer(ResellerProfileSerializer):
    """Admin serializer that allows setting the user field."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role=UserRole.RESELLER)
    )

    class Meta(ResellerProfileSerializer.Meta):
        read_only_fields = [
            "id",
            "group_root",
            "direct_downline_count",
            "created_at",
            "updated_at",
        ]


class AdminStaffProfileSerializer(StaffProfileSerializer):
    """Admin serializer that allows setting the user field."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role=UserRole.STAFF)
    )

    class Meta(StaffProfileSerializer.Meta):
        read_only_fields = ["id", "created_at", "updated_at"]


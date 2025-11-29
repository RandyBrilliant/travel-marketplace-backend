from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from account.models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    UserRole,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "full_name",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "date_joined",
        ]
        read_only_fields = ["is_staff", "is_superuser", "last_login", "date_joined"]


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
            "group_root",
            "own_commission_rate",
            "upline_commission_rate",
            "direct_downline_count",
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


class StaffProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            "id",
            "user",
            "job_title",
            "department",
            "contact_phone",
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
            "full_name",
            "password",
            "password_confirm",
            "role",
            "supplier_profile",
            "reseller_profile",
            "staff_profile",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "full_name": {"required": True},
            "role": {"required": True},
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

        # Remove password_confirm (not needed for user creation)
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")

        # Create the user
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            full_name=validated_data["full_name"],
            password=password,
            role=validated_data.get("role", UserRole.RESELLER),
        )

        # Create profile based on role
        if user.role == UserRole.SUPPLIER and supplier_profile_data:
            SupplierProfile.objects.create(user=user, **supplier_profile_data)
        elif user.role == UserRole.RESELLER and reseller_profile_data:
            ResellerProfile.objects.create(user=user, **reseller_profile_data)
        elif user.role == UserRole.STAFF and staff_profile_data:
            StaffProfile.objects.create(user=user, **staff_profile_data)

        return user
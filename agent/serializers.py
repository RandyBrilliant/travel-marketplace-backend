from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from account.models import CustomUser, SupplierApprovalStatus, SupplierProfile, UserRole
from itinerary.serializers import (
    ItineraryBoardCreateUpdateSerializer,
    ItineraryBoardListSerializer,
    ItineraryCardCreateUpdateSerializer,
    ItineraryColumnCreateUpdateSerializer,
)
from travel.serializers import (
    TourDateSerializer,
    TourImageCreateUpdateSerializer,
    TourPackageCreateUpdateSerializer,
    TourPackageSerializer,
)


def approved_suppliers():
    return SupplierProfile.objects.filter(
        approval_status=SupplierApprovalStatus.APPROVED,
        user__is_active=True,
    )


class AgentSupplierSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SupplierProfile
        fields = [
            "id",
            "company_name",
            "contact_person",
            "contact_phone",
            "email",
            "approval_status",
        ]


class AgentSupplierCreateSerializer(serializers.Serializer):
    """Staff-agent supplier registration. Creates an APPROVED supplier with no usable password."""

    email = serializers.EmailField()
    company_name = serializers.CharField(max_length=255)
    contact_person = serializers.CharField(max_length=255)
    contact_phone = serializers.CharField(max_length=50)
    address = serializers.CharField(required=False, allow_blank=True, default="")
    allow_duplicate_name = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        email = value.lower().strip()
        existing = CustomUser.objects.filter(email__iexact=email).first()
        if existing:
            profile = SupplierProfile.objects.filter(user=existing).first()
            if profile:
                raise serializers.ValidationError(
                    f"A supplier with this email already exists (supplier_id={profile.id}, "
                    f"company_name={profile.company_name!r}, status={profile.approval_status})."
                )
            raise serializers.ValidationError(
                "A non-supplier user with this email already exists. Use a different email "
                "or convert the account in the admin panel."
            )
        return email

    def validate_company_name(self, value):
        return value.strip()

    def validate(self, attrs):
        if not attrs.get("allow_duplicate_name"):
            clashes = SupplierProfile.objects.filter(
                company_name__iexact=attrs["company_name"]
            ).select_related("user")
            if clashes.exists():
                raise serializers.ValidationError(
                    {
                        "company_name": [
                            "A supplier with this company name already exists: "
                            + ", ".join(
                                f"supplier_id={p.id} ({p.user.email}, {p.approval_status})"
                                for p in clashes[:5]
                            )
                            + ". Use the existing supplier, or pass allow_duplicate_name=true "
                            "if this is genuinely a different company."
                        ]
                    }
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        approver = self.context["request"].user
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            password=None,
            role=UserRole.SUPPLIER,
            is_active=True,
        )
        return SupplierProfile.objects.create(
            user=user,
            company_name=validated_data["company_name"],
            contact_person=validated_data["contact_person"].strip(),
            contact_phone=validated_data["contact_phone"].strip(),
            address=validated_data.get("address", "").strip(),
            approval_status=SupplierApprovalStatus.APPROVED,
            approved_by=approver,
            approved_at=timezone.now(),
        )


class AgentTourCreateSerializer(TourPackageCreateUpdateSerializer):
    supplier = serializers.PrimaryKeyRelatedField(
        queryset=approved_suppliers(),
        required=False,
    )

    class Meta(TourPackageCreateUpdateSerializer.Meta):
        fields = TourPackageCreateUpdateSerializer.Meta.fields + ["supplier"]
        read_only_fields = [
            field
            for field in TourPackageCreateUpdateSerializer.Meta.read_only_fields
            if field != "supplier"
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.instance and not attrs.get("supplier"):
            raise serializers.ValidationError({"supplier": "Supplier wajib diisi."})
        return attrs

    def create(self, validated_data):
        validated_data["is_active"] = False
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("is_active", None)
        return super().update(instance, validated_data)


class AgentTourSerializer(TourPackageSerializer):
    admin_url = serializers.SerializerMethodField()

    class Meta(TourPackageSerializer.Meta):
        fields = list(TourPackageSerializer.Meta.fields) + ["admin_url"]

    def get_admin_url(self, obj):
        from django.conf import settings

        base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
        return f"{base}/admin/tours/{obj.slug}" if base else ""


class AgentBoardCreateSerializer(ItineraryBoardCreateUpdateSerializer):
    supplier = serializers.PrimaryKeyRelatedField(
        queryset=approved_suppliers(),
        required=False,
    )

    def create(self, validated_data):
        validated_data["is_active"] = False
        validated_data["is_public"] = False
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("is_active", None)
        validated_data.pop("is_public", None)
        return super().update(instance, validated_data)


class AgentBoardListSerializer(ItineraryBoardListSerializer):
    admin_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta(ItineraryBoardListSerializer.Meta):
        fields = list(ItineraryBoardListSerializer.Meta.fields) + ["admin_url", "status"]

    def get_admin_url(self, obj):
        from django.conf import settings

        base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
        return f"{base}/admin/itinerary-boards/{obj.slug}" if base else ""

    def get_status(self, obj):
        if obj.is_active and obj.is_public:
            return "published"
        return "draft"


class AgentPublishSerializer(serializers.Serializer):
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError(
                "Set confirm=true after the operator has reviewed the draft."
            )
        return value


class AgentTourImageSerializer(TourImageCreateUpdateSerializer):
    pass


class AgentTourDateSerializer(TourDateSerializer):
    pass


class AgentColumnCreateSerializer(ItineraryColumnCreateUpdateSerializer):
    pass


class AgentCardCreateSerializer(ItineraryCardCreateUpdateSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

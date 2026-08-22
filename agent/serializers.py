from rest_framework import serializers

from account.models import SupplierApprovalStatus, SupplierProfile
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

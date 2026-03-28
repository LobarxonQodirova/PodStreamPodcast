from rest_framework import serializers

from .models import SponsorDeal, Donation, PremiumContent


class SponsorDealSerializer(serializers.ModelSerializer):
    ad_type_display = serializers.CharField(source="get_ad_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    revenue_earned = serializers.ReadOnlyField()
    is_complete = serializers.ReadOnlyField()

    class Meta:
        model = SponsorDeal
        fields = [
            "id", "podcast", "sponsor_name", "sponsor_email",
            "sponsor_website", "sponsor_logo", "ad_type", "ad_type_display",
            "status", "status_display", "rate_per_episode", "total_episodes",
            "total_amount", "episodes_delivered", "revenue_earned",
            "is_complete", "start_date", "end_date",
            "talking_points", "promo_code", "tracking_url",
            "notes", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "episodes_delivered", "created_at", "updated_at",
        ]


class SponsorDealCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SponsorDeal
        fields = [
            "podcast", "sponsor_name", "sponsor_email",
            "sponsor_website", "sponsor_logo", "ad_type",
            "rate_per_episode", "total_episodes", "total_amount",
            "start_date", "end_date", "talking_points",
            "promo_code", "tracking_url", "notes",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        podcast = attrs.get("podcast")
        if podcast and request and podcast.owner != request.user:
            raise serializers.ValidationError(
                {"podcast": "You do not own this podcast."}
            )
        return attrs


class DonationSerializer(serializers.ModelSerializer):
    donor_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Donation
        fields = [
            "id", "donor_name", "podcast", "amount",
            "currency", "message", "is_anonymous",
            "status", "status_display", "created_at",
        ]

    def get_donor_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        if obj.donor:
            return obj.donor.display_name or obj.donor.email
        return "Guest"


class DonationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = ["podcast", "amount", "currency", "message", "is_anonymous"]

    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError("Minimum donation is $1.00.")
        if value > 10000:
            raise serializers.ValidationError("Maximum single donation is $10,000.")
        return value


class PremiumContentSerializer(serializers.ModelSerializer):
    content_type_display = serializers.CharField(
        source="get_content_type_display", read_only=True,
    )

    class Meta:
        model = PremiumContent
        fields = [
            "id", "podcast", "episode", "title", "description",
            "content_type", "content_type_display", "price",
            "is_subscriber_only", "audio_file", "duration",
            "is_published", "publish_date", "total_purchases",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "total_purchases", "created_at", "updated_at"]


class PremiumContentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumContent
        fields = [
            "podcast", "episode", "title", "description",
            "content_type", "price", "is_subscriber_only",
            "audio_file", "is_published", "publish_date",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        podcast = attrs.get("podcast")
        if podcast and request and podcast.owner != request.user:
            raise serializers.ValidationError(
                {"podcast": "You do not own this podcast."}
            )
        return attrs

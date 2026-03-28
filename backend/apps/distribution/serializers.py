from rest_framework import serializers

from .models import RSSFeed, DistributionChannel


class RSSFeedSerializer(serializers.ModelSerializer):
    podcast_title = serializers.CharField(source="podcast.title", read_only=True)

    class Meta:
        model = RSSFeed
        fields = [
            "id", "podcast", "podcast_title", "feed_url",
            "custom_domain", "itunes_id", "spotify_url",
            "google_podcasts_url", "episodes_per_page",
            "include_show_notes", "include_transcript_link",
            "redirect_url", "last_built", "created_at",
        ]
        read_only_fields = ["id", "feed_url", "last_built", "created_at"]


class RSSFeedUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSSFeed
        fields = [
            "custom_domain", "itunes_id", "spotify_url",
            "google_podcasts_url", "episodes_per_page",
            "include_show_notes", "include_transcript_link",
            "redirect_url",
        ]


class DistributionChannelSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(
        source="get_platform_display", read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True,
    )

    class Meta:
        model = DistributionChannel
        fields = [
            "id", "podcast", "platform", "platform_display",
            "status", "status_display", "external_url",
            "external_id", "submitted_at", "approved_at",
            "notes", "created_at",
        ]
        read_only_fields = [
            "id", "submitted_at", "approved_at", "created_at",
        ]


class DistributionChannelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistributionChannel
        fields = ["podcast", "platform", "external_url", "external_id", "notes"]

    def validate(self, attrs):
        podcast = attrs["podcast"]
        platform = attrs["platform"]
        if DistributionChannel.objects.filter(
            podcast=podcast, platform=platform
        ).exists():
            raise serializers.ValidationError(
                f"This podcast is already registered on {platform}."
            )
        return attrs

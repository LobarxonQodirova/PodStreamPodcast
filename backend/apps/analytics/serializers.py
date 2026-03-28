from rest_framework import serializers

from .models import EpisodeAnalytics, ListenerDemographics, DownloadStats


class EpisodeAnalyticsSerializer(serializers.ModelSerializer):
    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = EpisodeAnalytics
        fields = [
            "id", "episode", "episode_title", "date",
            "plays", "unique_listeners", "downloads",
            "total_listen_seconds", "average_listen_percentage",
            "completion_rate",
        ]


class ListenerDemographicsSerializer(serializers.ModelSerializer):
    device_type_display = serializers.CharField(
        source="get_device_type_display", read_only=True,
    )

    class Meta:
        model = ListenerDemographics
        fields = [
            "id", "podcast", "date", "country", "country_name",
            "region", "city", "device_type", "device_type_display",
            "app_name", "os_name", "listener_count",
        ]


class DownloadStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownloadStats
        fields = [
            "id", "episode", "source", "country", "city",
            "device_type", "os_name", "browser_or_app",
            "is_download", "listen_duration", "completed",
            "created_at",
        ]


class OverviewSerializer(serializers.Serializer):
    """Aggregated overview stats for the analytics dashboard."""
    total_plays = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    total_unique_listeners = serializers.IntegerField()
    total_subscribers = serializers.IntegerField()
    total_episodes = serializers.IntegerField()
    avg_listen_duration = serializers.FloatField()
    plays_trend = serializers.ListField(child=serializers.DictField())
    top_episodes = serializers.ListField(child=serializers.DictField())


class GeographySerializer(serializers.Serializer):
    """Geographic distribution of listeners."""
    country = serializers.CharField()
    country_name = serializers.CharField()
    listener_count = serializers.IntegerField()
    percentage = serializers.FloatField()


class DateRangeSerializer(serializers.Serializer):
    """Validate date range query parameters."""
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    podcast_id = serializers.UUIDField(required=False)
    episode_id = serializers.UUIDField(required=False)

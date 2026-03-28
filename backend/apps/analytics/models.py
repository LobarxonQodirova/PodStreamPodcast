import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.episodes.models import Episode
from apps.podcasts.models import Podcast


class EpisodeAnalytics(models.Model):
    """Per-episode analytics aggregated by date."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="analytics",
    )
    date = models.DateField(db_index=True)

    plays = models.PositiveIntegerField(default=0)
    unique_listeners = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    total_listen_seconds = models.BigIntegerField(default=0)
    average_listen_percentage = models.FloatField(
        default=0.0, help_text="Average percentage of episode listened",
    )
    completion_rate = models.FloatField(
        default=0.0, help_text="Percentage of listeners who finished the episode",
    )

    class Meta:
        db_table = "episode_analytics"
        unique_together = ["episode", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["episode", "-date"]),
            models.Index(fields=["-date"]),
        ]

    def __str__(self):
        return f"{self.episode.title} - {self.date}: {self.plays} plays"


class ListenerDemographics(models.Model):
    """Aggregated demographic data for a podcast's listeners."""

    class DeviceType(models.TextChoices):
        MOBILE = "mobile", _("Mobile")
        DESKTOP = "desktop", _("Desktop")
        TABLET = "tablet", _("Tablet")
        SMART_SPEAKER = "smart_speaker", _("Smart Speaker")
        OTHER = "other", _("Other")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="demographics",
    )
    date = models.DateField(db_index=True)

    # Geographic breakdown
    country = models.CharField(max_length=2, blank=True, help_text="ISO 3166-1 alpha-2")
    country_name = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Device breakdown
    device_type = models.CharField(
        max_length=15, choices=DeviceType.choices, default=DeviceType.OTHER,
    )
    app_name = models.CharField(max_length=100, blank=True, help_text="Podcast app name")
    os_name = models.CharField(max_length=50, blank=True)

    listener_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "listener_demographics"
        ordering = ["-date", "-listener_count"]
        indexes = [
            models.Index(fields=["podcast", "-date"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return f"{self.podcast.title} - {self.date} - {self.country}: {self.listener_count}"


class DownloadStats(models.Model):
    """Raw download/play event log for granular analytics."""

    class Source(models.TextChoices):
        DIRECT = "direct", _("Direct")
        RSS = "rss", _("RSS Feed")
        EMBED = "embed", _("Embed Player")
        API = "api", _("API")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="download_stats",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="download_stats",
    )

    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(max_length=500, blank=True)
    source = models.CharField(
        max_length=10, choices=Source.choices, default=Source.DIRECT,
    )

    # Geo info (populated asynchronously)
    country = models.CharField(max_length=2, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    # Device info (parsed from user agent)
    device_type = models.CharField(max_length=15, blank=True)
    os_name = models.CharField(max_length=50, blank=True)
    browser_or_app = models.CharField(max_length=100, blank=True)

    # Listening
    is_download = models.BooleanField(default=False)
    listen_duration = models.PositiveIntegerField(
        default=0, help_text="Seconds listened in this session",
    )
    completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "download_stats"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["episode", "-created_at"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["ip_address"]),
        ]

    def __str__(self):
        return f"Play: {self.episode.title} at {self.created_at}"

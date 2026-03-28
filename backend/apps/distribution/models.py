import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.podcasts.models import Podcast


class RSSFeed(models.Model):
    """RSS feed configuration and cache for a podcast."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.OneToOneField(
        Podcast, on_delete=models.CASCADE, related_name="rss_feed",
    )
    feed_url = models.URLField(
        max_length=500, unique=True, help_text="Public RSS feed URL",
    )
    custom_domain = models.CharField(
        max_length=200, blank=True,
        help_text="Custom domain for the feed URL",
    )
    itunes_id = models.CharField(
        max_length=20, blank=True, help_text="Apple Podcasts ID",
    )
    spotify_url = models.URLField(max_length=500, blank=True)
    google_podcasts_url = models.URLField(max_length=500, blank=True)

    # Feed settings
    episodes_per_page = models.PositiveIntegerField(default=50)
    include_show_notes = models.BooleanField(default=True)
    include_transcript_link = models.BooleanField(default=False)
    redirect_url = models.URLField(
        max_length=500, blank=True,
        help_text="Redirect URL for feed migration",
    )

    # Cache
    cached_xml = models.TextField(blank=True, help_text="Cached RSS XML")
    last_built = models.DateTimeField(blank=True, null=True)
    build_hash = models.CharField(
        max_length=64, blank=True,
        help_text="Hash of the last build to detect changes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rss_feeds"

    def __str__(self):
        return f"RSS: {self.podcast.title}"


class DistributionChannel(models.Model):
    """Tracks where a podcast is distributed beyond the native RSS feed."""

    class Platform(models.TextChoices):
        APPLE = "apple", _("Apple Podcasts")
        SPOTIFY = "spotify", _("Spotify")
        GOOGLE = "google", _("Google Podcasts")
        AMAZON = "amazon", _("Amazon Music")
        STITCHER = "stitcher", _("Stitcher")
        OVERCAST = "overcast", _("Overcast")
        POCKET_CASTS = "pocket_casts", _("Pocket Casts")
        YOUTUBE = "youtube", _("YouTube")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        PENDING = "pending", _("Submission Pending")
        SUBMITTED = "submitted", _("Submitted")
        APPROVED = "approved", _("Approved & Live")
        REJECTED = "rejected", _("Rejected")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="distribution_channels",
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING,
    )
    external_url = models.URLField(max_length=500, blank=True)
    external_id = models.CharField(max_length=100, blank=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "distribution_channels"
        unique_together = ["podcast", "platform"]
        ordering = ["platform"]

    def __str__(self):
        return f"{self.podcast.title} on {self.get_platform_display()}"

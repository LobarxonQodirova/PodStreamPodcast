import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.podcasts.models import Podcast


class Episode(models.Model):
    """Individual podcast episode."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PROCESSING = "processing", _("Processing")
        SCHEDULED = "scheduled", _("Scheduled")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    class EpisodeType(models.TextChoices):
        FULL = "full", _("Full Episode")
        TRAILER = "trailer", _("Trailer")
        BONUS = "bonus", _("Bonus")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="episodes",
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, db_index=True)
    description = models.TextField(max_length=10000)
    show_notes = models.TextField(blank=True, help_text="HTML or Markdown show notes")

    # Audio
    audio_file = models.FileField(upload_to="episodes/audio/%Y/%m/")
    audio_url = models.URLField(max_length=1000, blank=True, help_text="CDN URL after processing")
    duration = models.PositiveIntegerField(
        default=0, help_text="Duration in seconds",
    )
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    audio_format = models.CharField(max_length=10, default="mp3")
    waveform_data = models.JSONField(
        blank=True, null=True, help_text="Waveform peak data for visualization",
    )

    # Artwork
    cover_image = models.ImageField(
        upload_to="episodes/covers/%Y/%m/", blank=True, null=True,
    )

    # Metadata
    season_number = models.PositiveIntegerField(blank=True, null=True)
    episode_number = models.PositiveIntegerField(blank=True, null=True)
    episode_type = models.CharField(
        max_length=10, choices=EpisodeType.choices, default=EpisodeType.FULL,
    )
    is_explicit = models.BooleanField(default=False)
    guests = models.CharField(
        max_length=500, blank=True, help_text="Comma-separated guest names",
    )

    # Publishing
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFT, db_index=True,
    )
    is_published = models.BooleanField(default=False, db_index=True)
    publish_date = models.DateTimeField(blank=True, null=True)
    scheduled_date = models.DateTimeField(blank=True, null=True)

    # Statistics (denormalized)
    total_plays = models.BigIntegerField(default=0)
    total_downloads = models.BigIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    average_listen_duration = models.PositiveIntegerField(
        default=0, help_text="Average seconds listened",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "episodes"
        ordering = ["-publish_date", "-created_at"]
        unique_together = ["podcast", "slug"]
        indexes = [
            models.Index(fields=["podcast", "status"]),
            models.Index(fields=["podcast", "-publish_date"]),
            models.Index(fields=["-total_plays"]),
            models.Index(fields=["season_number", "episode_number"]),
        ]

    def __str__(self):
        prefix = ""
        if self.season_number and self.episode_number:
            prefix = f"S{self.season_number:02d}E{self.episode_number:02d} - "
        elif self.episode_number:
            prefix = f"E{self.episode_number:02d} - "
        return f"{prefix}{self.title}"

    @property
    def duration_display(self):
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Episode.objects.filter(podcast=self.podcast, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class EpisodeChapter(models.Model):
    """Chapter markers within an episode for navigation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="chapters",
    )
    title = models.CharField(max_length=200)
    start_time = models.PositiveIntegerField(help_text="Start time in seconds")
    end_time = models.PositiveIntegerField(
        blank=True, null=True, help_text="End time in seconds",
    )
    url = models.URLField(blank=True, help_text="Optional link for the chapter")
    image = models.ImageField(
        upload_to="episodes/chapters/", blank=True, null=True,
    )

    class Meta:
        db_table = "episode_chapters"
        ordering = ["start_time"]
        unique_together = ["episode", "start_time"]

    def __str__(self):
        return f"{self.episode.title} - {self.title} ({self.start_time}s)"


class EpisodeTranscript(models.Model):
    """Transcript for an episode, supports multiple formats."""

    class Format(models.TextChoices):
        PLAIN = "plain", _("Plain Text")
        SRT = "srt", _("SRT Subtitles")
        VTT = "vtt", _("WebVTT")
        JSON = "json", _("Timed JSON")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="transcripts",
    )
    content = models.TextField(help_text="Full transcript text")
    timed_content = models.JSONField(
        blank=True, null=True,
        help_text="Array of {start, end, text} for synchronized display",
    )
    format = models.CharField(
        max_length=10, choices=Format.choices, default=Format.PLAIN,
    )
    language = models.CharField(max_length=10, default="en")
    is_auto_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "episode_transcripts"
        unique_together = ["episode", "language", "format"]

    def __str__(self):
        return f"Transcript: {self.episode.title} ({self.language})"


class EpisodeComment(models.Model):
    """User comments on episodes with optional timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="episode_comments",
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE,
        blank=True, null=True, related_name="replies",
    )
    content = models.TextField(max_length=2000)
    timestamp = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Optional episode timestamp in seconds for contextual comments",
    )
    is_pinned = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "episode_comments"
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["episode", "-created_at"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} on {self.episode.title}: {self.content[:50]}"

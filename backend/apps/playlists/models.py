import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.episodes.models import Episode


class Playlist(models.Model):
    """User-created playlist of episodes."""

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        PRIVATE = "private", _("Private")
        UNLISTED = "unlisted", _("Unlisted")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playlists",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(max_length=1000, blank=True)
    cover_image = models.ImageField(
        upload_to="playlists/covers/%Y/%m/", blank=True, null=True,
    )
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE,
    )
    is_default = models.BooleanField(
        default=False, help_text="User's 'Liked Episodes' default playlist",
    )

    total_duration = models.PositiveIntegerField(
        default=0, help_text="Total duration in seconds",
    )
    episode_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "playlists"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.user})"

    def recalculate_stats(self):
        """Recalculate episode count and total duration."""
        entries = self.entries.select_related("episode")
        self.episode_count = entries.count()
        self.total_duration = sum(e.episode.duration for e in entries if e.episode)
        self.save(update_fields=["episode_count", "total_duration", "updated_at"])


class PlaylistEpisode(models.Model):
    """Episodes within a playlist, maintaining order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="entries",
    )
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="playlist_entries",
    )
    position = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "playlist_episodes"
        ordering = ["position"]
        unique_together = ["playlist", "episode"]

    def __str__(self):
        return f"{self.playlist.name} #{self.position}: {self.episode.title}"


class ListenHistory(models.Model):
    """Tracks what episodes a user has listened to and their progress."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listen_history",
    )
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="listen_records",
    )
    progress = models.PositiveIntegerField(
        default=0, help_text="Playback position in seconds",
    )
    completed = models.BooleanField(default=False)
    listen_count = models.PositiveIntegerField(default=1)
    total_listen_time = models.PositiveIntegerField(
        default=0, help_text="Total seconds spent listening",
    )

    started_at = models.DateTimeField(auto_now_add=True)
    last_played_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listen_history"
        unique_together = ["user", "episode"]
        ordering = ["-last_played_at"]
        indexes = [
            models.Index(fields=["user", "-last_played_at"]),
        ]

    def __str__(self):
        status = "completed" if self.completed else f"{self.progress}s"
        return f"{self.user} - {self.episode.title} ({status})"


class Queue(models.Model):
    """User's playback queue (Up Next)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="queue_entries",
    )
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="queue_entries",
    )
    position = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "queue"
        ordering = ["position"]
        unique_together = ["user", "episode"]

    def __str__(self):
        return f"{self.user} queue #{self.position}: {self.episode.title}"

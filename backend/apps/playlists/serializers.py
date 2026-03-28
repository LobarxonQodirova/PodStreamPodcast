from rest_framework import serializers
from apps.episodes.serializers import EpisodeListSerializer

from .models import Playlist, PlaylistEpisode, ListenHistory, Queue


class PlaylistEpisodeSerializer(serializers.ModelSerializer):
    episode = EpisodeListSerializer(read_only=True)

    class Meta:
        model = PlaylistEpisode
        fields = ["id", "episode", "position", "added_at"]


class PlaylistSerializer(serializers.ModelSerializer):
    entries = PlaylistEpisodeSerializer(many=True, read_only=True)
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = [
            "id", "name", "description", "cover_image",
            "visibility", "is_default", "total_duration",
            "duration_display", "episode_count", "entries",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "is_default", "total_duration",
            "episode_count", "created_at", "updated_at",
        ]

    def get_duration_display(self, obj):
        hours, remainder = divmod(obj.total_duration, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


class PlaylistCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = ["name", "description", "cover_image", "visibility"]


class AddToPlaylistSerializer(serializers.Serializer):
    episode_id = serializers.UUIDField()
    position = serializers.IntegerField(required=False, min_value=0)

    def validate_episode_id(self, value):
        from apps.episodes.models import Episode
        try:
            Episode.objects.get(pk=value, is_published=True)
        except Episode.DoesNotExist:
            raise serializers.ValidationError("Episode not found.")
        return value


class ReorderPlaylistSerializer(serializers.Serializer):
    """Accepts ordered list of episode IDs for reordering."""
    episode_ids = serializers.ListField(child=serializers.UUIDField())


class ListenHistorySerializer(serializers.ModelSerializer):
    episode = EpisodeListSerializer(read_only=True)

    class Meta:
        model = ListenHistory
        fields = [
            "id", "episode", "progress", "completed",
            "listen_count", "total_listen_time",
            "started_at", "last_played_at",
        ]
        read_only_fields = ["id", "listen_count", "total_listen_time", "started_at"]


class UpdateProgressSerializer(serializers.Serializer):
    episode_id = serializers.UUIDField()
    progress = serializers.IntegerField(min_value=0)
    completed = serializers.BooleanField(default=False)
    listen_duration = serializers.IntegerField(
        min_value=0, default=0,
        help_text="Seconds listened in this session",
    )


class QueueSerializer(serializers.ModelSerializer):
    episode = EpisodeListSerializer(read_only=True)

    class Meta:
        model = Queue
        fields = ["id", "episode", "position", "added_at"]


class AddToQueueSerializer(serializers.Serializer):
    episode_id = serializers.UUIDField()

    def validate_episode_id(self, value):
        from apps.episodes.models import Episode
        try:
            Episode.objects.get(pk=value, is_published=True)
        except Episode.DoesNotExist:
            raise serializers.ValidationError("Episode not found.")
        return value

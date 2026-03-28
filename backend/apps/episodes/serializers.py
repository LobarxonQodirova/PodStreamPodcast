from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Episode, EpisodeChapter, EpisodeTranscript, EpisodeComment

User = get_user_model()


class EpisodeChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpisodeChapter
        fields = ["id", "title", "start_time", "end_time", "url", "image"]


class EpisodeTranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpisodeTranscript
        fields = [
            "id", "content", "timed_content", "format",
            "language", "is_auto_generated", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CommentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "display_name", "avatar"]


class EpisodeCommentSerializer(serializers.ModelSerializer):
    user = CommentUserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = EpisodeComment
        fields = [
            "id", "user", "parent", "content", "timestamp",
            "is_pinned", "likes_count", "replies",
            "is_owner", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "is_pinned", "likes_count", "created_at", "updated_at"]

    def get_replies(self, obj):
        if obj.replies.exists():
            return EpisodeCommentSerializer(
                obj.replies.select_related("user").order_by("created_at"),
                many=True,
                context=self.context,
            ).data
        return []

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return request and request.user == obj.user


class EpisodeCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpisodeComment
        fields = ["content", "timestamp", "parent"]

    def validate_parent(self, value):
        if value and value.parent is not None:
            raise serializers.ValidationError("Cannot reply to a reply. Only one level of nesting allowed.")
        return value


class EpisodeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for episode lists."""

    podcast_title = serializers.CharField(source="podcast.title", read_only=True)
    podcast_slug = serializers.CharField(source="podcast.slug", read_only=True)
    podcast_cover = serializers.ImageField(source="podcast.cover_image", read_only=True)
    duration_display = serializers.ReadOnlyField()

    class Meta:
        model = Episode
        fields = [
            "id", "title", "slug", "podcast_title", "podcast_slug",
            "podcast_cover", "cover_image", "description",
            "season_number", "episode_number", "episode_type",
            "duration", "duration_display", "is_explicit",
            "status", "is_published", "publish_date",
            "total_plays", "total_downloads", "total_comments",
            "created_at",
        ]


class EpisodeDetailSerializer(serializers.ModelSerializer):
    """Full serializer for episode detail with chapters and transcript."""

    podcast_title = serializers.CharField(source="podcast.title", read_only=True)
    podcast_slug = serializers.CharField(source="podcast.slug", read_only=True)
    podcast_cover = serializers.ImageField(source="podcast.cover_image", read_only=True)
    podcast_owner_id = serializers.UUIDField(source="podcast.owner_id", read_only=True)
    duration_display = serializers.ReadOnlyField()
    file_size_mb = serializers.ReadOnlyField()
    chapters = EpisodeChapterSerializer(many=True, read_only=True)
    has_transcript = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = [
            "id", "title", "slug", "podcast_title", "podcast_slug",
            "podcast_cover", "podcast_owner_id",
            "description", "show_notes", "audio_file", "audio_url",
            "duration", "duration_display", "file_size", "file_size_mb",
            "audio_format", "waveform_data", "cover_image",
            "season_number", "episode_number", "episode_type",
            "is_explicit", "guests", "status", "is_published",
            "publish_date", "scheduled_date",
            "total_plays", "total_downloads", "total_comments",
            "average_listen_duration", "chapters", "has_transcript",
            "created_at", "updated_at",
        ]

    def get_has_transcript(self, obj):
        return obj.transcripts.exists()


class EpisodeCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating episodes."""

    chapters = EpisodeChapterSerializer(many=True, required=False)

    class Meta:
        model = Episode
        fields = [
            "title", "description", "show_notes", "audio_file",
            "cover_image", "season_number", "episode_number",
            "episode_type", "is_explicit", "guests",
            "status", "scheduled_date", "chapters",
        ]

    def validate_audio_file(self, value):
        from django.conf import settings
        if value.size > settings.MAX_AUDIO_FILE_SIZE:
            max_mb = settings.MAX_AUDIO_FILE_SIZE / (1024 * 1024)
            raise serializers.ValidationError(
                f"Audio file too large. Maximum size is {max_mb:.0f} MB."
            )
        if value.content_type not in settings.ALLOWED_AUDIO_TYPES:
            raise serializers.ValidationError(
                f"Unsupported audio format: {value.content_type}. "
                f"Allowed: {', '.join(settings.ALLOWED_AUDIO_TYPES)}"
            )
        return value

    def create(self, validated_data):
        chapters_data = validated_data.pop("chapters", [])
        episode = Episode.objects.create(**validated_data)
        for chapter in chapters_data:
            EpisodeChapter.objects.create(episode=episode, **chapter)
        return episode

    def update(self, instance, validated_data):
        chapters_data = validated_data.pop("chapters", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if chapters_data is not None:
            instance.chapters.all().delete()
            for chapter in chapters_data:
                EpisodeChapter.objects.create(episode=instance, **chapter)
        return instance

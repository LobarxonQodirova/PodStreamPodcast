from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Podcast, PodcastCategory, PodcastTag, PodcastSubscription

User = get_user_model()


class PodcastCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    podcast_count = serializers.SerializerMethodField()

    class Meta:
        model = PodcastCategory
        fields = ["id", "name", "slug", "parent", "icon", "order", "subcategories", "podcast_count"]
        read_only_fields = ["slug"]

    def get_subcategories(self, obj):
        children = obj.subcategories.all()
        return PodcastCategorySerializer(children, many=True).data

    def get_podcast_count(self, obj):
        return obj.podcasts.filter(is_published=True).count()


class PodcastTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodcastTag
        fields = ["id", "name", "slug"]
        read_only_fields = ["slug"]


class PodcastOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "display_name", "avatar", "is_verified_podcaster"]


class PodcastListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for podcast listings."""

    owner = PodcastOwnerSerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    tags = PodcastTagSerializer(many=True, read_only=True)

    class Meta:
        model = Podcast
        fields = [
            "id", "title", "slug", "short_description", "cover_image",
            "owner", "category_name", "tags", "language", "content_rating",
            "is_published", "is_featured", "total_episodes",
            "total_subscribers", "total_plays", "average_rating",
            "publish_date", "created_at",
        ]


class PodcastDetailSerializer(serializers.ModelSerializer):
    """Full serializer for podcast detail view."""

    owner = PodcastOwnerSerializer(read_only=True)
    category = PodcastCategorySerializer(read_only=True)
    tags = PodcastTagSerializer(many=True, read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    episode_count = serializers.SerializerMethodField()

    class Meta:
        model = Podcast
        fields = [
            "id", "title", "slug", "description", "short_description",
            "cover_image", "banner_image", "owner", "category", "tags",
            "language", "content_rating", "website", "author_name",
            "author_email", "copyright_text", "is_published", "is_featured",
            "publish_date", "total_episodes", "total_subscribers",
            "total_plays", "average_rating", "is_subscribed",
            "episode_count", "created_at", "updated_at",
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return PodcastSubscription.objects.filter(
                user=request.user, podcast=obj
            ).exists()
        return False

    def get_episode_count(self, obj):
        return obj.episodes.filter(is_published=True).count() if hasattr(obj, "episodes") else 0


class PodcastCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating podcasts."""

    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True, required=False,
    )

    class Meta:
        model = Podcast
        fields = [
            "title", "description", "short_description",
            "cover_image", "banner_image", "category",
            "tag_names", "language", "content_rating",
            "website", "author_name", "author_email",
            "copyright_text", "is_published",
        ]

    def validate_title(self, value):
        user = self.context["request"].user
        qs = Podcast.objects.filter(owner=user, title__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a podcast with this title.")
        return value

    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", [])
        validated_data["owner"] = self.context["request"].user
        podcast = Podcast.objects.create(**validated_data)
        self._set_tags(podcast, tag_names)
        return podcast

    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tag_names is not None:
            self._set_tags(instance, tag_names)
        return instance

    def _set_tags(self, podcast, tag_names):
        tags = []
        for name in tag_names:
            tag, _ = PodcastTag.objects.get_or_create(
                name__iexact=name, defaults={"name": name}
            )
            tags.append(tag)
        podcast.tags.set(tags)


class PodcastSubscriptionSerializer(serializers.ModelSerializer):
    podcast = PodcastListSerializer(read_only=True)

    class Meta:
        model = PodcastSubscription
        fields = ["id", "podcast", "notify_new_episodes", "subscribed_at"]
        read_only_fields = ["id", "subscribed_at"]


class SubscribeSerializer(serializers.Serializer):
    """Serializer for subscribing/unsubscribing to a podcast."""

    podcast_id = serializers.UUIDField()
    notify_new_episodes = serializers.BooleanField(default=True)

    def validate_podcast_id(self, value):
        try:
            Podcast.objects.get(pk=value, is_published=True)
        except Podcast.DoesNotExist:
            raise serializers.ValidationError("Podcast not found or not published.")
        return value

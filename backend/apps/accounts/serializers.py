from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that includes user info in the token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["display_name"] = user.display_name or user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "email", "password", "password_confirm",
            "display_name", "role",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        # Listeners can only self-register as listener or podcaster
        role = attrs.get("role", User.Role.LISTENER)
        if role == User.Role.ADMIN:
            raise serializers.ValidationError(
                {"role": "Cannot register as admin."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile data."""

    storage_used_mb = serializers.ReadOnlyField()
    podcast_count = serializers.SerializerMethodField()
    subscriber_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "display_name", "bio",
            "avatar", "website", "twitter_handle", "role",
            "is_verified_podcaster", "podcaster_since",
            "storage_used_mb", "storage_limit",
            "email_on_new_episode", "email_on_comment",
            "email_on_subscription", "email_digest_weekly",
            "podcast_count", "subscriber_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "email", "role", "is_verified_podcaster",
            "podcaster_since", "storage_used_mb", "storage_limit",
            "created_at", "updated_at",
        ]

    def get_podcast_count(self, obj):
        if hasattr(obj, "podcasts"):
            return obj.podcasts.count()
        return 0

    def get_subscriber_count(self, obj):
        if hasattr(obj, "podcasts"):
            from apps.podcasts.models import PodcastSubscription
            return PodcastSubscription.objects.filter(
                podcast__owner=obj
            ).count()
        return 0


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            "display_name", "bio", "avatar", "website",
            "twitter_handle", "email_on_new_episode",
            "email_on_comment", "email_on_subscription",
            "email_digest_weekly",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        return attrs


class PublicPodcasterSerializer(serializers.ModelSerializer):
    """Public-facing serializer for podcaster profiles."""

    podcast_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "display_name", "bio", "avatar",
            "website", "twitter_handle", "is_verified_podcaster",
            "podcast_count", "created_at",
        ]

    def get_podcast_count(self, obj):
        return obj.podcasts.filter(is_published=True).count()

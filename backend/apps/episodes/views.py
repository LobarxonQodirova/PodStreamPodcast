from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.podcasts.models import Podcast
from apps.accounts.permissions import IsPodcaster, IsPodcastOwner

from .models import Episode, EpisodeChapter, EpisodeTranscript, EpisodeComment
from .serializers import (
    EpisodeListSerializer,
    EpisodeDetailSerializer,
    EpisodeCreateUpdateSerializer,
    EpisodeCommentSerializer,
    EpisodeCommentCreateSerializer,
    EpisodeTranscriptSerializer,
    EpisodeChapterSerializer,
)


class PodcastEpisodeListCreateView(generics.ListCreateAPIView):
    """List episodes for a podcast or create a new episode."""

    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["publish_date", "created_at", "total_plays", "episode_number"]
    ordering = ["-publish_date"]
    filterset_fields = ["status", "season_number", "episode_type"]

    def get_podcast(self):
        return get_object_or_404(Podcast, slug=self.kwargs["podcast_slug"])

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EpisodeCreateUpdateSerializer
        return EpisodeListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsPodcaster()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        podcast = self.get_podcast()
        qs = Episode.objects.filter(podcast=podcast).select_related("podcast")
        if not (
            self.request.user.is_authenticated
            and self.request.user == podcast.owner
        ):
            qs = qs.filter(is_published=True)
        return qs

    def perform_create(self, serializer):
        podcast = self.get_podcast()
        if podcast.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not own this podcast.")

        episode = serializer.save(podcast=podcast, file_size=serializer.validated_data["audio_file"].size)

        # Trigger audio processing task
        from .tasks import process_audio
        process_audio.delay(str(episode.id))

        # Update podcast episode count
        podcast.total_episodes = podcast.episodes.filter(is_published=True).count()
        podcast.save(update_fields=["total_episodes"])


class EpisodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an episode."""

    lookup_field = "slug"
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return EpisodeCreateUpdateSerializer
        return EpisodeDetailSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [permissions.IsAuthenticated(), IsPodcastOwner()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return (
            Episode.objects.filter(podcast__slug=self.kwargs["podcast_slug"])
            .select_related("podcast__owner")
            .prefetch_related("chapters", "transcripts")
        )


class RecordPlayView(APIView):
    """Record a play event for an episode."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, episode_id):
        try:
            episode = Episode.objects.get(pk=episode_id, is_published=True)
        except Episode.DoesNotExist:
            return Response({"detail": "Episode not found."}, status=status.HTTP_404_NOT_FOUND)

        Episode.objects.filter(pk=episode_id).update(total_plays=F("total_plays") + 1)
        Podcast.objects.filter(pk=episode.podcast_id).update(total_plays=F("total_plays") + 1)

        # Record analytics asynchronously
        from apps.analytics.services import AnalyticsService
        AnalyticsService.record_play(
            episode=episode,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response({"detail": "Play recorded."}, status=status.HTTP_200_OK)


class RecordDownloadView(APIView):
    """Record a download event for an episode."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, episode_id):
        try:
            episode = Episode.objects.get(pk=episode_id, is_published=True)
        except Episode.DoesNotExist:
            return Response({"detail": "Episode not found."}, status=status.HTTP_404_NOT_FOUND)

        Episode.objects.filter(pk=episode_id).update(total_downloads=F("total_downloads") + 1)

        return Response({"detail": "Download recorded."}, status=status.HTTP_200_OK)


class EpisodeCommentListCreateView(generics.ListCreateAPIView):
    """List or create comments on an episode."""

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EpisodeCommentCreateSerializer
        return EpisodeCommentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return (
            EpisodeComment.objects.filter(
                episode_id=self.kwargs["episode_id"],
                parent__isnull=True,
            )
            .select_related("user")
            .prefetch_related("replies__user")
        )

    def perform_create(self, serializer):
        episode = get_object_or_404(Episode, pk=self.kwargs["episode_id"], is_published=True)
        comment = serializer.save(user=self.request.user, episode=episode)
        Episode.objects.filter(pk=episode.pk).update(total_comments=F("total_comments") + 1)

        # Notify podcast owner
        from apps.notifications.services import NotificationService
        NotificationService.notify_new_comment(comment)


class EpisodeCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete a comment."""

    serializer_class = EpisodeCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return EpisodeComment.objects.filter(user=self.request.user)


class EpisodeTranscriptView(generics.ListCreateAPIView):
    """List or upload transcripts for an episode."""

    serializer_class = EpisodeTranscriptSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsPodcaster()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return EpisodeTranscript.objects.filter(episode_id=self.kwargs["episode_id"])

    def perform_create(self, serializer):
        episode = get_object_or_404(Episode, pk=self.kwargs["episode_id"])
        if episode.podcast.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not own this podcast.")
        serializer.save(episode=episode)


class LatestEpisodesView(generics.ListAPIView):
    """List the most recent published episodes across all podcasts."""

    serializer_class = EpisodeListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Episode.objects.filter(is_published=True)
            .select_related("podcast")
            .order_by("-publish_date")[:50]
        )

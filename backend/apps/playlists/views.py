from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import F

from apps.episodes.models import Episode

from .models import Playlist, PlaylistEpisode, ListenHistory, Queue
from .serializers import (
    PlaylistSerializer,
    PlaylistCreateSerializer,
    AddToPlaylistSerializer,
    ReorderPlaylistSerializer,
    ListenHistorySerializer,
    UpdateProgressSerializer,
    QueueSerializer,
    AddToQueueSerializer,
)


class PlaylistListCreateView(generics.ListCreateAPIView):
    """List user's playlists or create a new one."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PlaylistCreateSerializer
        return PlaylistSerializer

    def get_queryset(self):
        return (
            Playlist.objects.filter(user=self.request.user)
            .prefetch_related("entries__episode__podcast")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PlaylistDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a playlist."""

    serializer_class = PlaylistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Playlist.objects.filter(user=self.request.user).prefetch_related(
            "entries__episode__podcast"
        )

    def perform_destroy(self, instance):
        if instance.is_default:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot delete the default playlist.")
        instance.delete()


class PlaylistAddEpisodeView(APIView):
    """Add an episode to a playlist."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
        serializer = AddToPlaylistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        episode = Episode.objects.get(pk=serializer.validated_data["episode_id"])
        position = serializer.validated_data.get("position", playlist.episode_count)

        entry, created = PlaylistEpisode.objects.get_or_create(
            playlist=playlist,
            episode=episode,
            defaults={"position": position},
        )

        if created:
            playlist.recalculate_stats()
            return Response(
                {"detail": "Episode added to playlist."},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"detail": "Episode already in playlist."},
            status=status.HTTP_200_OK,
        )


class PlaylistRemoveEpisodeView(APIView):
    """Remove an episode from a playlist."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, episode_id):
        playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
        deleted, _ = PlaylistEpisode.objects.filter(
            playlist=playlist, episode_id=episode_id
        ).delete()

        if deleted:
            playlist.recalculate_stats()
            return Response({"detail": "Episode removed."}, status=status.HTTP_200_OK)
        return Response({"detail": "Episode not in playlist."}, status=status.HTTP_404_NOT_FOUND)


class PlaylistReorderView(APIView):
    """Reorder episodes in a playlist."""

    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
        serializer = ReorderPlaylistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        episode_ids = serializer.validated_data["episode_ids"]
        for position, eid in enumerate(episode_ids):
            PlaylistEpisode.objects.filter(
                playlist=playlist, episode_id=eid
            ).update(position=position)

        return Response({"detail": "Playlist reordered."}, status=status.HTTP_200_OK)


class ListenHistoryListView(generics.ListAPIView):
    """List user's listening history."""

    serializer_class = ListenHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            ListenHistory.objects.filter(user=self.request.user)
            .select_related("episode__podcast")
            .order_by("-last_played_at")
        )


class UpdateProgressView(APIView):
    """Update listening progress for an episode."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UpdateProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        history, created = ListenHistory.objects.get_or_create(
            user=request.user,
            episode_id=data["episode_id"],
            defaults={
                "progress": data["progress"],
                "completed": data["completed"],
                "total_listen_time": data.get("listen_duration", 0),
            },
        )

        if not created:
            history.progress = data["progress"]
            history.completed = data["completed"]
            history.listen_count = F("listen_count") + 1
            history.total_listen_time = F("total_listen_time") + data.get("listen_duration", 0)
            history.save()

        return Response({"detail": "Progress updated."}, status=status.HTTP_200_OK)


class ClearHistoryView(APIView):
    """Clear all listening history."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        ListenHistory.objects.filter(user=request.user).delete()
        return Response({"detail": "History cleared."}, status=status.HTTP_200_OK)


class QueueListView(generics.ListAPIView):
    """List the user's playback queue."""

    serializer_class = QueueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Queue.objects.filter(user=self.request.user)
            .select_related("episode__podcast")
            .order_by("position")
        )


class QueueManageView(APIView):
    """Add or remove episodes from the queue."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Add episode to end of queue."""
        serializer = AddToQueueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        last_position = Queue.objects.filter(user=request.user).count()
        entry, created = Queue.objects.get_or_create(
            user=request.user,
            episode_id=serializer.validated_data["episode_id"],
            defaults={"position": last_position},
        )

        if created:
            return Response({"detail": "Added to queue."}, status=status.HTTP_201_CREATED)
        return Response({"detail": "Already in queue."}, status=status.HTTP_200_OK)

    def delete(self, request):
        """Remove episode from queue."""
        episode_id = request.data.get("episode_id")
        deleted, _ = Queue.objects.filter(
            user=request.user, episode_id=episode_id
        ).delete()

        if deleted:
            # Reorder remaining items
            for i, entry in enumerate(Queue.objects.filter(user=request.user).order_by("position")):
                entry.position = i
                entry.save(update_fields=["position"])
            return Response({"detail": "Removed from queue."}, status=status.HTTP_200_OK)
        return Response({"detail": "Not in queue."}, status=status.HTTP_404_NOT_FOUND)


class QueueClearView(APIView):
    """Clear the entire queue."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        Queue.objects.filter(user=request.user).delete()
        return Response({"detail": "Queue cleared."}, status=status.HTTP_200_OK)

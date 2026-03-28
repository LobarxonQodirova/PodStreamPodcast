from datetime import date, timedelta

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.podcasts.models import Podcast
from apps.episodes.models import Episode
from apps.accounts.permissions import IsPodcaster

from .models import EpisodeAnalytics, ListenerDemographics, DownloadStats
from .serializers import (
    EpisodeAnalyticsSerializer,
    ListenerDemographicsSerializer,
    DownloadStatsSerializer,
    OverviewSerializer,
    DateRangeSerializer,
)
from .services import AnalyticsService


class AnalyticsOverviewView(APIView):
    """Dashboard overview stats for a podcast."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get(self, request):
        podcast_id = request.query_params.get("podcast_id")
        if not podcast_id:
            return Response({"detail": "podcast_id is required."}, status=400)

        podcast = get_object_or_404(Podcast, pk=podcast_id, owner=request.user)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            start_date = date.fromisoformat(start_date)
        if end_date:
            end_date = date.fromisoformat(end_date)

        overview = AnalyticsService.get_podcast_overview(
            podcast, start_date=start_date, end_date=end_date
        )
        serializer = OverviewSerializer(overview)
        return Response(serializer.data)


class EpisodeAnalyticsView(APIView):
    """Detailed analytics for a specific episode."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get(self, request, episode_id):
        episode = get_object_or_404(
            Episode, pk=episode_id, podcast__owner=request.user
        )

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            start_date = date.fromisoformat(start_date)
        if end_date:
            end_date = date.fromisoformat(end_date)

        data = AnalyticsService.get_episode_analytics(
            episode, start_date=start_date, end_date=end_date
        )
        return Response(data)


class DownloadStatsView(generics.ListAPIView):
    """List download/play events for analytics."""

    serializer_class = DownloadStatsSerializer
    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_queryset(self):
        podcast_id = self.request.query_params.get("podcast_id")
        qs = DownloadStats.objects.filter(
            episode__podcast__owner=self.request.user,
        ).select_related("episode")

        if podcast_id:
            qs = qs.filter(episode__podcast_id=podcast_id)

        episode_id = self.request.query_params.get("episode_id")
        if episode_id:
            qs = qs.filter(episode_id=episode_id)

        start_date = self.request.query_params.get("start_date")
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)

        end_date = self.request.query_params.get("end_date")
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        return qs.order_by("-created_at")


class GeographyView(APIView):
    """Geographic breakdown of listeners."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get(self, request):
        podcast_id = request.query_params.get("podcast_id")
        if not podcast_id:
            return Response({"detail": "podcast_id is required."}, status=400)

        podcast = get_object_or_404(Podcast, pk=podcast_id, owner=request.user)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            start_date = date.fromisoformat(start_date)
        if end_date:
            end_date = date.fromisoformat(end_date)

        data = AnalyticsService.get_geography(
            podcast, start_date=start_date, end_date=end_date
        )
        return Response(data)


class DemographicsView(APIView):
    """Device and platform breakdown."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get(self, request):
        podcast_id = request.query_params.get("podcast_id")
        if not podcast_id:
            return Response({"detail": "podcast_id is required."}, status=400)

        podcast = get_object_or_404(Podcast, pk=podcast_id, owner=request.user)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            start_date = date.fromisoformat(start_date)
        if end_date:
            end_date = date.fromisoformat(end_date)

        device_data = AnalyticsService.get_device_breakdown(
            podcast, start_date=start_date, end_date=end_date
        )
        return Response({"devices": device_data})

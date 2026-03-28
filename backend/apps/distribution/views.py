from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.podcasts.models import Podcast
from apps.accounts.permissions import IsPodcaster, IsPodcastOwner

from .models import RSSFeed, DistributionChannel
from .serializers import (
    RSSFeedSerializer,
    RSSFeedUpdateSerializer,
    DistributionChannelSerializer,
    DistributionChannelCreateSerializer,
)
from .services import RSSFeedService


class RSSFeedView(generics.RetrieveUpdateAPIView):
    """View and configure the RSS feed for a podcast."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return RSSFeedUpdateSerializer
        return RSSFeedSerializer

    def get_object(self):
        podcast = get_object_or_404(
            Podcast, slug=self.kwargs["podcast_slug"], owner=self.request.user
        )
        return RSSFeedService.get_or_create_feed(podcast)


class RSSFeedXMLView(APIView):
    """Serve the RSS feed as XML (public endpoint)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, podcast_slug):
        podcast = get_object_or_404(Podcast, slug=podcast_slug, is_published=True)
        xml = RSSFeedService.get_cached_feed(podcast)
        if xml:
            return HttpResponse(xml, content_type="application/rss+xml; charset=utf-8")
        return HttpResponse(
            "<rss><channel><title>Feed unavailable</title></channel></rss>",
            content_type="application/rss+xml",
            status=503,
        )


class RebuildFeedView(APIView):
    """Manually trigger a feed rebuild."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def post(self, request, podcast_slug):
        podcast = get_object_or_404(
            Podcast, slug=podcast_slug, owner=request.user
        )
        xml = RSSFeedService.build_feed(podcast)
        if xml:
            return Response({"detail": "Feed rebuilt successfully."})
        return Response(
            {"detail": "Failed to rebuild feed."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class DistributionChannelListCreateView(generics.ListCreateAPIView):
    """List or add distribution channels for a podcast."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DistributionChannelCreateSerializer
        return DistributionChannelSerializer

    def get_queryset(self):
        return DistributionChannel.objects.filter(
            podcast__slug=self.kwargs["podcast_slug"],
            podcast__owner=self.request.user,
        )


class DistributionChannelDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage a specific distribution channel."""

    serializer_class = DistributionChannelSerializer
    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_queryset(self):
        return DistributionChannel.objects.filter(
            podcast__owner=self.request.user,
        )

from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F

from .models import Podcast, PodcastCategory, PodcastTag, PodcastSubscription
from .serializers import (
    PodcastListSerializer,
    PodcastDetailSerializer,
    PodcastCreateUpdateSerializer,
    PodcastCategorySerializer,
    PodcastTagSerializer,
    PodcastSubscriptionSerializer,
    SubscribeSerializer,
)
from apps.accounts.permissions import IsPodcaster, IsOwnerOrReadOnly


class PodcastListCreateView(generics.ListCreateAPIView):
    """List published podcasts or create a new one."""

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "author_name"]
    ordering_fields = ["created_at", "total_subscribers", "total_plays", "average_rating"]
    ordering = ["-created_at"]
    filterset_fields = ["category", "language", "content_rating", "is_featured"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PodcastCreateUpdateSerializer
        return PodcastListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsPodcaster()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Podcast.objects.select_related("owner", "category").prefetch_related("tags")
        if self.request.method == "GET":
            if not (self.request.user.is_authenticated and self.request.user.is_admin):
                qs = qs.filter(is_published=True)
        return qs


class PodcastDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a podcast by slug."""

    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return PodcastCreateUpdateSerializer
        return PodcastDetailSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return Podcast.objects.select_related("owner", "category").prefetch_related("tags")


class MyPodcastsView(generics.ListAPIView):
    """List the current user's own podcasts."""

    serializer_class = PodcastListSerializer
    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_queryset(self):
        return (
            Podcast.objects.filter(owner=self.request.user)
            .select_related("owner", "category")
            .prefetch_related("tags")
            .order_by("-created_at")
        )


class TrendingPodcastsView(generics.ListAPIView):
    """Return trending podcasts based on recent subscriber growth."""

    serializer_class = PodcastListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Podcast.objects.filter(is_published=True)
            .select_related("owner", "category")
            .prefetch_related("tags")
            .order_by("-total_subscribers", "-total_plays")[:50]
        )


class FeaturedPodcastsView(generics.ListAPIView):
    """Return editorially featured podcasts."""

    serializer_class = PodcastListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Podcast.objects.filter(is_published=True, is_featured=True)
            .select_related("owner", "category")
            .prefetch_related("tags")
            .order_by("-created_at")
        )


class CategoryListView(generics.ListAPIView):
    """List all podcast categories."""

    serializer_class = PodcastCategorySerializer
    permission_classes = [permissions.AllowAny]
    queryset = PodcastCategory.objects.filter(parent__isnull=True).prefetch_related("subcategories")


class CategoryPodcastsView(generics.ListAPIView):
    """List podcasts in a specific category."""

    serializer_class = PodcastListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return (
            Podcast.objects.filter(
                Q(category__slug=slug) | Q(category__parent__slug=slug),
                is_published=True,
            )
            .select_related("owner", "category")
            .prefetch_related("tags")
            .order_by("-total_subscribers")
        )


class TagListView(generics.ListAPIView):
    """List popular tags."""

    serializer_class = PodcastTagSerializer
    permission_classes = [permissions.AllowAny]
    queryset = PodcastTag.objects.all()


class SubscribeView(APIView):
    """Subscribe or unsubscribe from a podcast."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        podcast = Podcast.objects.get(pk=serializer.validated_data["podcast_id"])
        sub, created = PodcastSubscription.objects.get_or_create(
            user=request.user,
            podcast=podcast,
            defaults={"notify_new_episodes": serializer.validated_data["notify_new_episodes"]},
        )
        if created:
            podcast.total_subscribers = F("total_subscribers") + 1
            podcast.save(update_fields=["total_subscribers"])
            return Response(
                {"detail": "Subscribed successfully.", "subscription": PodcastSubscriptionSerializer(sub).data},
                status=status.HTTP_201_CREATED,
            )
        return Response({"detail": "Already subscribed."}, status=status.HTTP_200_OK)

    def delete(self, request):
        podcast_id = request.data.get("podcast_id")
        try:
            sub = PodcastSubscription.objects.get(user=request.user, podcast_id=podcast_id)
            sub.delete()
            Podcast.objects.filter(pk=podcast_id, total_subscribers__gt=0).update(
                total_subscribers=F("total_subscribers") - 1
            )
            return Response({"detail": "Unsubscribed."}, status=status.HTTP_200_OK)
        except PodcastSubscription.DoesNotExist:
            return Response({"detail": "Not subscribed."}, status=status.HTTP_404_NOT_FOUND)


class MySubscriptionsView(generics.ListAPIView):
    """List the current user's podcast subscriptions."""

    serializer_class = PodcastSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            PodcastSubscription.objects.filter(user=self.request.user)
            .select_related("podcast__owner", "podcast__category")
            .order_by("-subscribed_at")
        )

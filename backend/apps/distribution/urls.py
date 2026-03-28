from django.urls import path
from . import views

app_name = "distribution"

urlpatterns = [
    # RSS Feed
    path(
        "<slug:podcast_slug>/feed/",
        views.RSSFeedView.as_view(),
        name="rss-feed-config",
    ),
    path(
        "<slug:podcast_slug>/feed.xml",
        views.RSSFeedXMLView.as_view(),
        name="rss-feed-xml",
    ),
    path(
        "<slug:podcast_slug>/feed/rebuild/",
        views.RebuildFeedView.as_view(),
        name="rss-feed-rebuild",
    ),

    # Distribution Channels
    path(
        "<slug:podcast_slug>/channels/",
        views.DistributionChannelListCreateView.as_view(),
        name="channel-list-create",
    ),
    path(
        "channels/<uuid:pk>/",
        views.DistributionChannelDetailView.as_view(),
        name="channel-detail",
    ),
]

from django.urls import path
from . import views

app_name = "episodes"

urlpatterns = [
    # Episodes within a podcast
    path(
        "<slug:podcast_slug>/",
        views.PodcastEpisodeListCreateView.as_view(),
        name="episode-list-create",
    ),
    path(
        "<slug:podcast_slug>/<slug:slug>/",
        views.EpisodeDetailView.as_view(),
        name="episode-detail",
    ),

    # Tracking
    path(
        "play/<uuid:episode_id>/",
        views.RecordPlayView.as_view(),
        name="record-play",
    ),
    path(
        "download/<uuid:episode_id>/",
        views.RecordDownloadView.as_view(),
        name="record-download",
    ),

    # Comments
    path(
        "comments/<uuid:episode_id>/",
        views.EpisodeCommentListCreateView.as_view(),
        name="comment-list-create",
    ),
    path(
        "comments/detail/<uuid:pk>/",
        views.EpisodeCommentDetailView.as_view(),
        name="comment-detail",
    ),

    # Transcripts
    path(
        "transcripts/<uuid:episode_id>/",
        views.EpisodeTranscriptView.as_view(),
        name="transcript-list-create",
    ),

    # Discovery
    path(
        "discover/latest/",
        views.LatestEpisodesView.as_view(),
        name="latest-episodes",
    ),
]

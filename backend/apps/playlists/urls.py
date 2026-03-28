from django.urls import path
from . import views

app_name = "playlists"

urlpatterns = [
    # Playlists
    path("", views.PlaylistListCreateView.as_view(), name="playlist-list-create"),
    path("<uuid:pk>/", views.PlaylistDetailView.as_view(), name="playlist-detail"),
    path("<uuid:pk>/add/", views.PlaylistAddEpisodeView.as_view(), name="playlist-add"),
    path(
        "<uuid:pk>/remove/<uuid:episode_id>/",
        views.PlaylistRemoveEpisodeView.as_view(),
        name="playlist-remove",
    ),
    path("<uuid:pk>/reorder/", views.PlaylistReorderView.as_view(), name="playlist-reorder"),

    # Listen History
    path("history/", views.ListenHistoryListView.as_view(), name="history-list"),
    path("history/progress/", views.UpdateProgressView.as_view(), name="update-progress"),
    path("history/clear/", views.ClearHistoryView.as_view(), name="clear-history"),

    # Queue
    path("queue/", views.QueueListView.as_view(), name="queue-list"),
    path("queue/manage/", views.QueueManageView.as_view(), name="queue-manage"),
    path("queue/clear/", views.QueueClearView.as_view(), name="queue-clear"),
]

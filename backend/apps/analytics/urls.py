from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("overview/", views.AnalyticsOverviewView.as_view(), name="overview"),
    path("episodes/<uuid:episode_id>/", views.EpisodeAnalyticsView.as_view(), name="episode-analytics"),
    path("downloads/", views.DownloadStatsView.as_view(), name="download-stats"),
    path("geography/", views.GeographyView.as_view(), name="geography"),
    path("demographics/", views.DemographicsView.as_view(), name="demographics"),
]

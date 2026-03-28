from django.urls import path
from . import views

app_name = "podcasts"

urlpatterns = [
    # Podcast CRUD
    path("", views.PodcastListCreateView.as_view(), name="podcast-list-create"),
    path("<slug:slug>/", views.PodcastDetailView.as_view(), name="podcast-detail"),

    # Discovery
    path("discover/trending/", views.TrendingPodcastsView.as_view(), name="trending"),
    path("discover/featured/", views.FeaturedPodcastsView.as_view(), name="featured"),

    # Categories & Tags
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/podcasts/", views.CategoryPodcastsView.as_view(), name="category-podcasts"),
    path("tags/", views.TagListView.as_view(), name="tag-list"),

    # User-specific
    path("my/podcasts/", views.MyPodcastsView.as_view(), name="my-podcasts"),

    # Subscriptions
    path("subscriptions/", views.MySubscriptionsView.as_view(), name="my-subscriptions"),
    path("subscriptions/manage/", views.SubscribeView.as_view(), name="subscribe"),
]

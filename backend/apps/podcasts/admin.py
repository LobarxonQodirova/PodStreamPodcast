from django.contrib import admin
from .models import Podcast, PodcastCategory, PodcastTag, PodcastSubscription


@admin.register(PodcastCategory)
class PodcastCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "slug", "order"]
    list_filter = ["parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order", "name"]


@admin.register(PodcastTag)
class PodcastTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = [
        "title", "owner", "category", "is_published", "is_featured",
        "total_episodes", "total_subscribers", "total_plays", "created_at",
    ]
    list_filter = ["is_published", "is_featured", "category", "language", "content_rating"]
    search_fields = ["title", "description", "owner__email", "author_name"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["owner", "category"]
    filter_horizontal = ["tags"]
    readonly_fields = [
        "total_episodes", "total_subscribers", "total_plays",
        "average_rating", "created_at", "updated_at",
    ]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {
            "fields": ("owner", "title", "slug", "description", "short_description"),
        }),
        ("Media", {
            "fields": ("cover_image", "banner_image"),
        }),
        ("Classification", {
            "fields": ("category", "tags", "language", "content_rating"),
        }),
        ("Publishing", {
            "fields": ("is_published", "is_featured", "publish_date"),
        }),
        ("Author Info", {
            "fields": ("website", "author_name", "author_email", "copyright_text"),
        }),
        ("Statistics", {
            "fields": (
                "total_episodes", "total_subscribers",
                "total_plays", "average_rating",
            ),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(PodcastSubscription)
class PodcastSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "podcast", "notify_new_episodes", "subscribed_at"]
    list_filter = ["notify_new_episodes"]
    raw_id_fields = ["user", "podcast"]
    search_fields = ["user__email", "podcast__title"]
    date_hierarchy = "subscribed_at"

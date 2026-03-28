from django.contrib import admin
from .models import Episode, EpisodeChapter, EpisodeTranscript, EpisodeComment


class EpisodeChapterInline(admin.TabularInline):
    model = EpisodeChapter
    extra = 0
    fields = ["title", "start_time", "end_time", "url"]


class EpisodeTranscriptInline(admin.StackedInline):
    model = EpisodeTranscript
    extra = 0
    fields = ["language", "format", "is_auto_generated", "content"]


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = [
        "title", "podcast", "season_number", "episode_number",
        "status", "is_published", "duration", "total_plays",
        "total_downloads", "publish_date",
    ]
    list_filter = ["status", "is_published", "episode_type", "is_explicit", "podcast"]
    search_fields = ["title", "description", "podcast__title"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["podcast"]
    readonly_fields = [
        "total_plays", "total_downloads", "total_comments",
        "average_listen_duration", "file_size", "duration",
        "waveform_data", "created_at", "updated_at",
    ]
    date_hierarchy = "publish_date"
    inlines = [EpisodeChapterInline, EpisodeTranscriptInline]

    fieldsets = (
        (None, {
            "fields": (
                "podcast", "title", "slug", "description", "show_notes",
            ),
        }),
        ("Audio", {
            "fields": (
                "audio_file", "audio_url", "duration", "file_size",
                "audio_format", "waveform_data",
            ),
        }),
        ("Metadata", {
            "fields": (
                "cover_image", "season_number", "episode_number",
                "episode_type", "is_explicit", "guests",
            ),
        }),
        ("Publishing", {
            "fields": ("status", "is_published", "publish_date", "scheduled_date"),
        }),
        ("Statistics", {
            "fields": (
                "total_plays", "total_downloads",
                "total_comments", "average_listen_duration",
            ),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(EpisodeComment)
class EpisodeCommentAdmin(admin.ModelAdmin):
    list_display = ["user", "episode", "content_preview", "timestamp", "is_pinned", "likes_count", "created_at"]
    list_filter = ["is_pinned", "created_at"]
    search_fields = ["content", "user__email", "episode__title"]
    raw_id_fields = ["user", "episode", "parent"]

    def content_preview(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    content_preview.short_description = "Content"

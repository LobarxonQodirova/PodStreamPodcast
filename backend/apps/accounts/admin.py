from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email", "display_name", "role", "is_verified_podcaster",
        "is_active", "is_staff", "created_at",
    ]
    list_filter = ["role", "is_verified_podcaster", "is_active", "is_staff"]
    search_fields = ["email", "display_name", "username"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "username", "display_name", "bio", "avatar",
                    "website", "twitter_handle",
                )
            },
        ),
        (
            _("Podcaster info"),
            {
                "fields": (
                    "role", "is_verified_podcaster", "podcaster_since",
                    "storage_used", "storage_limit",
                )
            },
        ),
        (
            _("Notification preferences"),
            {
                "fields": (
                    "email_on_new_episode", "email_on_comment",
                    "email_on_subscription", "email_digest_weekly",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active", "is_staff", "is_superuser",
                    "groups", "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email", "password1", "password2",
                    "display_name", "role",
                ),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

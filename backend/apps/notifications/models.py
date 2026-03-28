import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """In-app notification for users."""

    class NotificationType(models.TextChoices):
        NEW_EPISODE = "new_episode", _("New Episode")
        NEW_SUBSCRIBER = "new_subscriber", _("New Subscriber")
        NEW_COMMENT = "new_comment", _("New Comment")
        COMMENT_REPLY = "comment_reply", _("Comment Reply")
        DONATION = "donation", _("Donation Received")
        EPISODE_PROCESSED = "episode_processed", _("Episode Processed")
        SPONSOR_UPDATE = "sponsor_update", _("Sponsor Update")
        SYSTEM = "system", _("System Notification")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="sent_notifications",
    )

    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices,
    )
    title = models.CharField(max_length=200)
    message = models.TextField(max_length=1000)
    action_url = models.CharField(
        max_length=500, blank=True,
        help_text="Frontend URL to navigate to on click",
    )

    # Reference to related object
    content_type = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)

    is_read = models.BooleanField(default=False, db_index=True)
    is_emailed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self):
        status = "read" if self.is_read else "unread"
        return f"[{status}] {self.title} -> {self.recipient}"


class EmailQueue(models.Model):
    """Queue for outgoing email notifications."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=300)
    body_html = models.TextField()
    body_text = models.TextField(blank=True)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING,
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    notification = models.ForeignKey(
        Notification, on_delete=models.SET_NULL,
        blank=True, null=True, related_name="emails",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "email_queue"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Email to {self.recipient_email}: {self.subject} ({self.status})"

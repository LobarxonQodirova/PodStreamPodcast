import logging

from django.conf import settings

from .models import Notification, EmailQueue

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating in-app and email notifications."""

    @classmethod
    def create_notification(cls, recipient, notification_type, title, message,
                            sender=None, action_url="", content_type="",
                            object_id="", send_email=True):
        """Create an in-app notification and optionally queue an email."""
        notification = Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            content_type=content_type,
            object_id=object_id,
        )

        if send_email and cls._should_email(recipient, notification_type):
            cls._queue_email(notification)

        return notification

    @classmethod
    def notify_new_episode(cls, episode):
        """Notify all subscribers about a new episode."""
        from apps.podcasts.models import PodcastSubscription

        subscriptions = PodcastSubscription.objects.filter(
            podcast=episode.podcast,
            notify_new_episodes=True,
        ).select_related("user")

        notifications = []
        for sub in subscriptions:
            notifications.append(
                Notification(
                    recipient=sub.user,
                    sender=episode.podcast.owner,
                    notification_type=Notification.NotificationType.NEW_EPISODE,
                    title=f"New episode: {episode.title}",
                    message=(
                        f'{episode.podcast.title} just published "{episode.title}". '
                        f"Listen now!"
                    ),
                    action_url=f"/podcast/{episode.podcast.slug}/episode/{episode.slug}",
                    content_type="episode",
                    object_id=str(episode.id),
                )
            )

        created = Notification.objects.bulk_create(notifications, batch_size=500)
        logger.info(
            f"Created {len(created)} new episode notifications for '{episode.title}'."
        )

        # Queue emails for users with email preferences
        for notification in created:
            if cls._should_email(notification.recipient, Notification.NotificationType.NEW_EPISODE):
                cls._queue_email(notification)

        return len(created)

    @classmethod
    def notify_new_comment(cls, comment):
        """Notify the podcast owner about a new comment."""
        episode = comment.episode
        podcast_owner = episode.podcast.owner

        if comment.user == podcast_owner:
            return None

        notification = cls.create_notification(
            recipient=podcast_owner,
            sender=comment.user,
            notification_type=Notification.NotificationType.NEW_COMMENT,
            title=f"New comment on {episode.title}",
            message=(
                f'{comment.user.display_name or comment.user.email} commented: '
                f'"{comment.content[:100]}"'
            ),
            action_url=f"/podcast/{episode.podcast.slug}/episode/{episode.slug}#comments",
            content_type="comment",
            object_id=str(comment.id),
        )

        # Also notify parent comment author for replies
        if comment.parent and comment.parent.user != comment.user:
            cls.create_notification(
                recipient=comment.parent.user,
                sender=comment.user,
                notification_type=Notification.NotificationType.COMMENT_REPLY,
                title=f"Reply to your comment",
                message=(
                    f'{comment.user.display_name or comment.user.email} replied: '
                    f'"{comment.content[:100]}"'
                ),
                action_url=f"/podcast/{episode.podcast.slug}/episode/{episode.slug}#comments",
                content_type="comment",
                object_id=str(comment.id),
            )

        return notification

    @classmethod
    def notify_new_subscriber(cls, subscription):
        """Notify podcast owner of a new subscriber."""
        return cls.create_notification(
            recipient=subscription.podcast.owner,
            sender=subscription.user,
            notification_type=Notification.NotificationType.NEW_SUBSCRIBER,
            title="New subscriber!",
            message=(
                f"{subscription.user.display_name or subscription.user.email} "
                f"subscribed to {subscription.podcast.title}."
            ),
            action_url=f"/studio/{subscription.podcast.slug}/subscribers",
            content_type="subscription",
            object_id=str(subscription.id),
        )

    @classmethod
    def notify_donation(cls, donation):
        """Notify podcast owner of a donation."""
        donor_name = "Anonymous" if donation.is_anonymous else (
            donation.donor.display_name or donation.donor.email if donation.donor else "A listener"
        )
        return cls.create_notification(
            recipient=donation.podcast.owner,
            notification_type=Notification.NotificationType.DONATION,
            title=f"You received a ${donation.amount} tip!",
            message=(
                f"{donor_name} sent a ${donation.amount} tip for {donation.podcast.title}."
                + (f' Message: "{donation.message}"' if donation.message else "")
            ),
            action_url=f"/studio/{donation.podcast.slug}/monetization",
            content_type="donation",
            object_id=str(donation.id),
        )

    @classmethod
    def mark_as_read(cls, notification_id, user):
        """Mark a notification as read."""
        Notification.objects.filter(
            pk=notification_id, recipient=user
        ).update(is_read=True)

    @classmethod
    def mark_all_read(cls, user):
        """Mark all notifications as read for a user."""
        Notification.objects.filter(
            recipient=user, is_read=False
        ).update(is_read=True)

    @classmethod
    def get_unread_count(cls, user):
        """Get count of unread notifications."""
        return Notification.objects.filter(
            recipient=user, is_read=False
        ).count()

    @classmethod
    def _should_email(cls, user, notification_type):
        """Check user preferences for email notifications."""
        type_map = {
            Notification.NotificationType.NEW_EPISODE: user.email_on_new_episode,
            Notification.NotificationType.NEW_COMMENT: user.email_on_comment,
            Notification.NotificationType.COMMENT_REPLY: user.email_on_comment,
            Notification.NotificationType.NEW_SUBSCRIBER: user.email_on_subscription,
        }
        return type_map.get(notification_type, False)

    @classmethod
    def _queue_email(cls, notification):
        """Queue an email for a notification."""
        EmailQueue.objects.create(
            recipient_email=notification.recipient.email,
            subject=notification.title,
            body_html=cls._render_email_html(notification),
            body_text=notification.message,
            notification=notification,
        )

    @staticmethod
    def _render_email_html(notification):
        """Render a simple HTML email body."""
        base_url = getattr(settings, "SITE_URL", "http://localhost:3000")
        action_link = ""
        if notification.action_url:
            action_link = (
                f'<p><a href="{base_url}{notification.action_url}" '
                f'style="background:#6366f1;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;display:inline-block;">'
                f'View Details</a></p>'
            )

        return f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <div style="background:#6366f1;padding:16px 24px;border-radius:8px 8px 0 0;">
                <h1 style="color:#fff;margin:0;font-size:20px;">PodStream</h1>
            </div>
            <div style="background:#fff;padding:24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;">
                <h2 style="color:#1f2937;margin-top:0;">{notification.title}</h2>
                <p style="color:#4b5563;line-height:1.6;">{notification.message}</p>
                {action_link}
            </div>
            <div style="text-align:center;padding:16px;color:#9ca3af;font-size:12px;">
                <p>You received this email because of your notification settings on PodStream.</p>
            </div>
        </div>
        """

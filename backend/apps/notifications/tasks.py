import logging

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_new_episode_notification(self, episode_id):
    """Send notifications (in-app + email) when a new episode is published."""
    from apps.episodes.models import Episode
    from .services import NotificationService

    try:
        episode = Episode.objects.select_related("podcast__owner").get(pk=episode_id)
        count = NotificationService.notify_new_episode(episode)
        logger.info(f"Sent {count} notifications for new episode: {episode.title}")
    except Episode.DoesNotExist:
        logger.error(f"Episode {episode_id} not found for notification.")
    except Exception as exc:
        logger.exception(f"Failed to send episode notifications: {exc}")
        raise self.retry(exc=exc)


@shared_task
def process_pending_notifications():
    """Process pending email notifications in the queue."""
    from .models import EmailQueue

    pending = EmailQueue.objects.filter(
        status=EmailQueue.Status.PENDING,
        attempts__lt=3,
    ).order_by("created_at")[:100]

    sent_count = 0
    for email_entry in pending:
        try:
            send_mail(
                subject=email_entry.subject,
                message=email_entry.body_text,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@podstream.com"),
                recipient_list=[email_entry.recipient_email],
                html_message=email_entry.body_html,
                fail_silently=False,
            )
            email_entry.status = EmailQueue.Status.SENT
            email_entry.sent_at = timezone.now()
            email_entry.save(update_fields=["status", "sent_at"])

            # Mark the notification as emailed
            if email_entry.notification:
                email_entry.notification.is_emailed = True
                email_entry.notification.save(update_fields=["is_emailed"])

            sent_count += 1

        except Exception as e:
            email_entry.attempts += 1
            email_entry.last_error = str(e)
            if email_entry.attempts >= 3:
                email_entry.status = EmailQueue.Status.FAILED
            email_entry.save(update_fields=["attempts", "last_error", "status"])
            logger.warning(
                f"Failed to send email to {email_entry.recipient_email}: {e}"
            )

    logger.info(f"Processed {sent_count}/{pending.count()} pending emails.")


@shared_task
def send_weekly_digest():
    """Send weekly digest emails to users who opted in."""
    from django.contrib.auth import get_user_model
    from apps.podcasts.models import PodcastSubscription
    from apps.episodes.models import Episode
    from datetime import timedelta

    User = get_user_model()
    week_ago = timezone.now() - timedelta(days=7)

    users = User.objects.filter(
        email_digest_weekly=True,
        is_active=True,
    )

    for user in users:
        subscribed_podcasts = PodcastSubscription.objects.filter(
            user=user
        ).values_list("podcast_id", flat=True)

        new_episodes = Episode.objects.filter(
            podcast_id__in=subscribed_podcasts,
            is_published=True,
            publish_date__gte=week_ago,
        ).select_related("podcast").order_by("-publish_date")[:20]

        if not new_episodes.exists():
            continue

        episode_list = "\n".join(
            f"- {ep.podcast.title}: {ep.title}"
            for ep in new_episodes
        )

        episode_html = "".join(
            f'<li style="margin-bottom:8px;">'
            f'<strong>{ep.podcast.title}</strong>: {ep.title}'
            f'</li>'
            for ep in new_episodes
        )

        subject = f"PodStream Weekly: {new_episodes.count()} new episodes from your subscriptions"
        body_text = (
            f"Hi {user.display_name or 'there'},\n\n"
            f"Here's what's new from your subscriptions this week:\n\n"
            f"{episode_list}\n\n"
            f"Listen now at http://localhost:3000\n\n"
            f"- The PodStream Team"
        )
        body_html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <div style="background:#6366f1;padding:16px 24px;border-radius:8px 8px 0 0;">
                <h1 style="color:#fff;margin:0;">PodStream Weekly Digest</h1>
            </div>
            <div style="background:#fff;padding:24px;border:1px solid #e5e7eb;">
                <p>Hi {user.display_name or 'there'},</p>
                <p>Here's what's new this week:</p>
                <ul>{episode_html}</ul>
                <p><a href="http://localhost:3000" style="background:#6366f1;color:#fff;
                    padding:12px 24px;border-radius:6px;text-decoration:none;
                    display:inline-block;">Listen Now</a></p>
            </div>
        </div>
        """

        from .models import EmailQueue
        EmailQueue.objects.create(
            recipient_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )

    logger.info(f"Queued weekly digest emails for {users.count()} users.")


@shared_task
def cleanup_old_notifications():
    """Delete read notifications older than 90 days."""
    from .models import Notification
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=90)
    count, _ = Notification.objects.filter(
        is_read=True,
        created_at__lt=cutoff,
    ).delete()
    logger.info(f"Cleaned up {count} old read notifications.")

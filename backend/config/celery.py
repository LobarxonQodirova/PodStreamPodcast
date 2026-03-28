"""
Celery configuration for PodStream project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("podstream")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    "aggregate-daily-analytics": {
        "task": "apps.analytics.tasks.aggregate_daily_analytics",
        "schedule": crontab(hour=1, minute=0),  # 1:00 AM daily
    },
    "cleanup-expired-sessions": {
        "task": "apps.accounts.tasks.cleanup_expired_sessions",
        "schedule": crontab(hour=3, minute=0),  # 3:00 AM daily
    },
    "update-rss-feeds": {
        "task": "apps.distribution.tasks.update_all_rss_feeds",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "send-new-episode-notifications": {
        "task": "apps.notifications.tasks.process_pending_notifications",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "cleanup-stale-uploads": {
        "task": "apps.episodes.tasks.cleanup_stale_uploads",
        "schedule": crontab(hour=4, minute=0),  # 4:00 AM daily
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")

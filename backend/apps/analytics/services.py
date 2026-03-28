import logging
from datetime import date, timedelta

from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone

from apps.episodes.models import Episode
from apps.podcasts.models import Podcast
from .models import EpisodeAnalytics, ListenerDemographics, DownloadStats

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for recording and querying analytics data."""

    @classmethod
    def record_play(cls, episode, user=None, ip_address="", user_agent=""):
        """Record a play event asynchronously."""
        device_info = cls._parse_user_agent(user_agent)
        geo_info = cls._lookup_geo(ip_address)

        DownloadStats.objects.create(
            episode=episode,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            source=DownloadStats.Source.DIRECT,
            is_download=False,
            device_type=device_info.get("device_type", ""),
            os_name=device_info.get("os_name", ""),
            browser_or_app=device_info.get("browser_or_app", ""),
            country=geo_info.get("country", ""),
            city=geo_info.get("city", ""),
            latitude=geo_info.get("latitude"),
            longitude=geo_info.get("longitude"),
        )

    @classmethod
    def get_podcast_overview(cls, podcast, start_date=None, end_date=None):
        """Get aggregated overview stats for a podcast."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        episodes = Episode.objects.filter(podcast=podcast)
        analytics = EpisodeAnalytics.objects.filter(
            episode__podcast=podcast,
            date__gte=start_date,
            date__lte=end_date,
        )

        totals = analytics.aggregate(
            total_plays=Sum("plays"),
            total_downloads=Sum("downloads"),
            total_unique_listeners=Sum("unique_listeners"),
            avg_listen_duration=Avg("total_listen_seconds"),
        )

        # Daily trend
        plays_trend = list(
            analytics.values("date")
            .annotate(plays=Sum("plays"), downloads=Sum("downloads"))
            .order_by("date")
        )

        # Top episodes
        top_episodes = list(
            episodes.filter(is_published=True)
            .order_by("-total_plays")[:10]
            .values("id", "title", "total_plays", "total_downloads")
        )

        return {
            "total_plays": totals["total_plays"] or 0,
            "total_downloads": totals["total_downloads"] or 0,
            "total_unique_listeners": totals["total_unique_listeners"] or 0,
            "total_subscribers": podcast.total_subscribers,
            "total_episodes": episodes.filter(is_published=True).count(),
            "avg_listen_duration": round(totals["avg_listen_duration"] or 0, 1),
            "plays_trend": plays_trend,
            "top_episodes": top_episodes,
        }

    @classmethod
    def get_episode_analytics(cls, episode, start_date=None, end_date=None):
        """Get detailed analytics for a specific episode."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        analytics = EpisodeAnalytics.objects.filter(
            episode=episode,
            date__gte=start_date,
            date__lte=end_date,
        ).order_by("date")

        return list(analytics.values(
            "date", "plays", "unique_listeners", "downloads",
            "total_listen_seconds", "average_listen_percentage",
            "completion_rate",
        ))

    @classmethod
    def get_geography(cls, podcast, start_date=None, end_date=None):
        """Get geographic breakdown of listeners."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        demographics = (
            ListenerDemographics.objects.filter(
                podcast=podcast,
                date__gte=start_date,
                date__lte=end_date,
            )
            .values("country", "country_name")
            .annotate(listener_count=Sum("listener_count"))
            .order_by("-listener_count")[:50]
        )

        total = sum(d["listener_count"] for d in demographics) or 1
        results = []
        for d in demographics:
            results.append({
                "country": d["country"],
                "country_name": d["country_name"],
                "listener_count": d["listener_count"],
                "percentage": round((d["listener_count"] / total) * 100, 1),
            })
        return results

    @classmethod
    def get_device_breakdown(cls, podcast, start_date=None, end_date=None):
        """Get device type breakdown."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        return list(
            ListenerDemographics.objects.filter(
                podcast=podcast,
                date__gte=start_date,
                date__lte=end_date,
            )
            .values("device_type")
            .annotate(count=Sum("listener_count"))
            .order_by("-count")
        )

    @classmethod
    def aggregate_daily(cls, target_date=None):
        """Aggregate raw download stats into daily analytics. Run via Celery beat."""
        if not target_date:
            target_date = date.today() - timedelta(days=1)

        logger.info(f"Aggregating analytics for {target_date}")

        # Get all episodes with plays on that date
        stats = DownloadStats.objects.filter(
            created_at__date=target_date,
        ).values("episode_id").annotate(
            plays=Count("id", filter=Q(is_download=False)),
            downloads=Count("id", filter=Q(is_download=True)),
            unique_listeners=Count("ip_address", distinct=True),
            total_seconds=Sum("listen_duration"),
        )

        for stat in stats:
            episode_id = stat["episode_id"]
            try:
                episode = Episode.objects.get(pk=episode_id)
            except Episode.DoesNotExist:
                continue

            avg_pct = 0.0
            if episode.duration > 0 and stat["unique_listeners"] > 0 and stat["total_seconds"]:
                avg_pct = min(
                    100.0,
                    (stat["total_seconds"] / (episode.duration * stat["unique_listeners"])) * 100,
                )

            completed_count = DownloadStats.objects.filter(
                episode_id=episode_id,
                created_at__date=target_date,
                completed=True,
            ).count()
            completion_rate = (
                (completed_count / stat["unique_listeners"] * 100)
                if stat["unique_listeners"] > 0
                else 0.0
            )

            EpisodeAnalytics.objects.update_or_create(
                episode_id=episode_id,
                date=target_date,
                defaults={
                    "plays": stat["plays"],
                    "downloads": stat["downloads"],
                    "unique_listeners": stat["unique_listeners"],
                    "total_listen_seconds": stat["total_seconds"] or 0,
                    "average_listen_percentage": round(avg_pct, 1),
                    "completion_rate": round(completion_rate, 1),
                },
            )

        # Aggregate demographics
        demo_stats = (
            DownloadStats.objects.filter(created_at__date=target_date)
            .exclude(country="")
            .values("episode__podcast_id", "country", "device_type")
            .annotate(count=Count("id"))
        )

        for demo in demo_stats:
            ListenerDemographics.objects.update_or_create(
                podcast_id=demo["episode__podcast_id"],
                date=target_date,
                country=demo["country"],
                device_type=demo["device_type"] or "other",
                defaults={"listener_count": demo["count"]},
            )

        logger.info(f"Analytics aggregation complete for {target_date}")

    @staticmethod
    def _parse_user_agent(user_agent_string):
        """Parse user agent to extract device/browser info."""
        result = {
            "device_type": "other",
            "os_name": "",
            "browser_or_app": "",
        }
        if not user_agent_string:
            return result

        try:
            from user_agents import parse
            ua = parse(user_agent_string)
            if ua.is_mobile:
                result["device_type"] = "mobile"
            elif ua.is_tablet:
                result["device_type"] = "tablet"
            elif ua.is_pc:
                result["device_type"] = "desktop"
            result["os_name"] = str(ua.os.family)
            result["browser_or_app"] = str(ua.browser.family)
        except ImportError:
            ua_lower = user_agent_string.lower()
            if any(kw in ua_lower for kw in ["mobile", "iphone", "android"]):
                result["device_type"] = "mobile"
            elif "tablet" in ua_lower or "ipad" in ua_lower:
                result["device_type"] = "tablet"
            else:
                result["device_type"] = "desktop"
        return result

    @staticmethod
    def _lookup_geo(ip_address):
        """Lookup geographic info from IP address using GeoIP2."""
        result = {
            "country": "",
            "city": "",
            "latitude": None,
            "longitude": None,
        }
        if not ip_address or ip_address in ("127.0.0.1", "::1"):
            return result

        try:
            from django.contrib.gis.geoip2 import GeoIP2
            g = GeoIP2()
            geo_data = g.city(ip_address)
            result["country"] = geo_data.get("country_code", "")
            result["city"] = geo_data.get("city", "")
            result["latitude"] = geo_data.get("latitude")
            result["longitude"] = geo_data.get("longitude")
        except Exception:
            pass
        return result

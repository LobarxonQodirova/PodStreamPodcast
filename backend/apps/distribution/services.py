import hashlib
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone
from feedgen.feed import FeedGenerator

from apps.podcasts.models import Podcast
from apps.episodes.models import Episode
from .models import RSSFeed

logger = logging.getLogger(__name__)


class RSSFeedService:
    """Service for generating and caching RSS feeds."""

    @classmethod
    def get_or_create_feed(cls, podcast):
        """Get or create the RSSFeed record for a podcast."""
        feed, created = RSSFeed.objects.get_or_create(
            podcast=podcast,
            defaults={
                "feed_url": cls._build_feed_url(podcast),
            },
        )
        if created:
            cls.build_feed(podcast)
        return feed

    @classmethod
    def build_feed(cls, podcast):
        """Generate the RSS XML for a podcast."""
        try:
            rss_feed = RSSFeed.objects.get(podcast=podcast)
        except RSSFeed.DoesNotExist:
            logger.error(f"No RSSFeed record for podcast {podcast.id}")
            return None

        episodes = (
            Episode.objects.filter(podcast=podcast, is_published=True)
            .order_by("-publish_date")[:rss_feed.episodes_per_page]
        )

        fg = FeedGenerator()
        fg.load_extension("podcast")

        # Channel info
        fg.title(podcast.title)
        fg.link(href=podcast.website or cls._build_podcast_url(podcast))
        fg.description(podcast.description)
        fg.language(podcast.language)
        fg.copyright(podcast.copyright_text or f"Copyright {datetime.now().year} {podcast.author_name}")
        fg.managingEditor(podcast.author_email or "")
        fg.lastBuildDate(timezone.now())

        # iTunes metadata
        fg.podcast.itunes_author(podcast.author_name)
        fg.podcast.itunes_summary(podcast.short_description or podcast.description[:300])
        fg.podcast.itunes_explicit("yes" if podcast.content_rating == "explicit" else "no")
        if podcast.category:
            fg.podcast.itunes_category(podcast.category.name)
        if podcast.cover_image:
            fg.podcast.itunes_image(cls._media_url(podcast.cover_image.url))
        fg.podcast.itunes_owner(
            name=podcast.author_name,
            email=podcast.author_email,
        )

        # Episodes
        for ep in episodes:
            fe = fg.add_entry()
            fe.id(str(ep.id))
            fe.title(ep.title)
            fe.description(ep.description)
            fe.published(ep.publish_date or ep.created_at)

            if ep.audio_url:
                audio_url = ep.audio_url
            elif ep.audio_file:
                audio_url = cls._media_url(ep.audio_file.url)
            else:
                continue

            fe.enclosure(
                url=audio_url,
                length=str(ep.file_size),
                type=f"audio/{ep.audio_format}",
            )

            fe.podcast.itunes_duration(ep.duration)
            fe.podcast.itunes_explicit("yes" if ep.is_explicit else "no")
            fe.podcast.itunes_episode_type(ep.episode_type)

            if ep.season_number:
                fe.podcast.itunes_season(ep.season_number)
            if ep.episode_number:
                fe.podcast.itunes_episode(ep.episode_number)

            if rss_feed.include_show_notes and ep.show_notes:
                fe.content(content=ep.show_notes, type="html")

        # Generate XML
        xml_content = fg.rss_str(pretty=True).decode("utf-8")
        content_hash = hashlib.sha256(xml_content.encode()).hexdigest()

        # Update cache
        rss_feed.cached_xml = xml_content
        rss_feed.last_built = timezone.now()
        rss_feed.build_hash = content_hash
        rss_feed.save(update_fields=["cached_xml", "last_built", "build_hash"])

        logger.info(f"RSS feed built for '{podcast.title}' with {episodes.count()} episodes.")
        return xml_content

    @classmethod
    def get_cached_feed(cls, podcast):
        """Return cached feed XML, rebuilding if stale."""
        try:
            rss_feed = RSSFeed.objects.get(podcast=podcast)
        except RSSFeed.DoesNotExist:
            return cls.build_feed(podcast)

        if rss_feed.cached_xml:
            return rss_feed.cached_xml

        return cls.build_feed(podcast)

    @staticmethod
    def _build_feed_url(podcast):
        base = getattr(settings, "SITE_URL", "http://localhost:8000")
        return f"{base}/api/v1/distribution/{podcast.slug}/feed.xml"

    @staticmethod
    def _build_podcast_url(podcast):
        base = getattr(settings, "SITE_URL", "http://localhost:3000")
        return f"{base}/podcast/{podcast.slug}"

    @staticmethod
    def _media_url(relative_url):
        if relative_url.startswith("http"):
            return relative_url
        base = getattr(settings, "SITE_URL", "http://localhost:8000")
        return f"{base}{relative_url}"

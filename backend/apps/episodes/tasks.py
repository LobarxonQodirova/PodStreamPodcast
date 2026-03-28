import logging
import os
import tempfile

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_audio(self, episode_id):
    """
    Process an uploaded audio file:
    1. Validate and extract metadata (duration, format)
    2. Transcode to standardized MP3 if needed
    3. Generate waveform peak data for visualization
    4. Update episode record with processed data
    """
    from .models import Episode

    try:
        episode = Episode.objects.select_related("podcast__owner").get(pk=episode_id)
    except Episode.DoesNotExist:
        logger.error(f"Episode {episode_id} not found for processing.")
        return

    episode.status = Episode.Status.PROCESSING
    episode.save(update_fields=["status"])

    try:
        from mutagen import File as MutagenFile
        from pydub import AudioSegment

        audio_path = episode.audio_file.path
        logger.info(f"Processing audio for episode '{episode.title}': {audio_path}")

        # Extract metadata with mutagen
        audio_meta = MutagenFile(audio_path)
        if audio_meta and audio_meta.info:
            episode.duration = int(audio_meta.info.length)
        episode.file_size = os.path.getsize(audio_path)

        # Transcode to MP3 if not already
        if not audio_path.lower().endswith(".mp3"):
            logger.info(f"Transcoding {audio_path} to MP3...")
            audio = AudioSegment.from_file(audio_path)
            mp3_path = tempfile.mktemp(suffix=".mp3")
            audio.export(
                mp3_path,
                format="mp3",
                bitrate=settings.AUDIO_BITRATE,
                parameters=["-ar", str(settings.AUDIO_SAMPLE_RATE)],
            )
            # Replace the original file
            with open(mp3_path, "rb") as f:
                from django.core.files.base import ContentFile
                episode.audio_file.save(
                    os.path.basename(audio_path).rsplit(".", 1)[0] + ".mp3",
                    ContentFile(f.read()),
                    save=False,
                )
            os.unlink(mp3_path)
            episode.audio_format = "mp3"
            episode.file_size = episode.audio_file.size

        # Generate waveform data
        episode.waveform_data = generate_waveform_data(episode.audio_file.path)

        # Update owner storage usage
        owner = episode.podcast.owner
        owner.storage_used += episode.file_size
        owner.save(update_fields=["storage_used"])

        # Mark as ready
        if episode.scheduled_date and episode.scheduled_date > timezone.now():
            episode.status = Episode.Status.SCHEDULED
        else:
            episode.status = Episode.Status.PUBLISHED
            episode.is_published = True
            episode.publish_date = timezone.now()

        episode.save()
        logger.info(f"Audio processing complete for episode '{episode.title}'.")

        # Notify subscribers
        from apps.notifications.tasks import send_new_episode_notification
        if episode.is_published:
            send_new_episode_notification.delay(str(episode.id))

    except Exception as exc:
        logger.exception(f"Audio processing failed for episode {episode_id}: {exc}")
        episode.status = Episode.Status.DRAFT
        episode.save(update_fields=["status"])
        raise self.retry(exc=exc)


def generate_waveform_data(audio_path, num_peaks=200):
    """Generate waveform peak data for audio visualization."""
    try:
        from pydub import AudioSegment
        import struct

        audio = AudioSegment.from_file(audio_path)
        samples = audio.get_array_of_samples()

        if len(samples) == 0:
            return [0] * num_peaks

        chunk_size = max(1, len(samples) // num_peaks)
        peaks = []
        for i in range(0, len(samples), chunk_size):
            chunk = samples[i : i + chunk_size]
            if chunk:
                peak = max(abs(min(chunk)), abs(max(chunk)))
                peaks.append(peak)

        if not peaks:
            return [0] * num_peaks

        # Normalize to 0-100 range
        max_peak = max(peaks) or 1
        normalized = [round((p / max_peak) * 100) for p in peaks[:num_peaks]]

        # Pad if necessary
        while len(normalized) < num_peaks:
            normalized.append(0)

        return normalized

    except Exception as e:
        logger.warning(f"Waveform generation failed: {e}")
        return [0] * num_peaks


@shared_task
def generate_waveform(episode_id):
    """Regenerate waveform data for an episode."""
    from .models import Episode

    try:
        episode = Episode.objects.get(pk=episode_id)
        episode.waveform_data = generate_waveform_data(episode.audio_file.path)
        episode.save(update_fields=["waveform_data"])
        logger.info(f"Waveform regenerated for episode '{episode.title}'.")
    except Episode.DoesNotExist:
        logger.error(f"Episode {episode_id} not found for waveform generation.")


@shared_task
def transcribe_episode(episode_id):
    """
    Placeholder for automatic transcription.
    In production, this would call a speech-to-text service
    (e.g., Whisper, Google Speech-to-Text, AWS Transcribe).
    """
    from .models import Episode, EpisodeTranscript

    try:
        episode = Episode.objects.get(pk=episode_id)
        logger.info(f"Transcription requested for episode '{episode.title}'.")

        # Placeholder: In production, call STT API here
        # transcript_text = stt_service.transcribe(episode.audio_file.path)

        transcript_text = f"[Auto-transcription pending for: {episode.title}]"
        EpisodeTranscript.objects.update_or_create(
            episode=episode,
            language="en",
            format=EpisodeTranscript.Format.PLAIN,
            defaults={
                "content": transcript_text,
                "is_auto_generated": True,
            },
        )
        logger.info(f"Transcription placeholder created for '{episode.title}'.")
    except Episode.DoesNotExist:
        logger.error(f"Episode {episode_id} not found for transcription.")


@shared_task
def cleanup_stale_uploads():
    """Remove draft episodes older than 30 days with no audio file."""
    from .models import Episode
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=30)
    stale = Episode.objects.filter(
        status=Episode.Status.DRAFT,
        created_at__lt=cutoff,
        audio_file="",
    )
    count = stale.count()
    stale.delete()
    logger.info(f"Cleaned up {count} stale draft episodes.")


@shared_task
def publish_scheduled_episodes():
    """Publish episodes whose scheduled_date has passed."""
    from .models import Episode

    now = timezone.now()
    episodes = Episode.objects.filter(
        status=Episode.Status.SCHEDULED,
        scheduled_date__lte=now,
    )
    for episode in episodes:
        episode.status = Episode.Status.PUBLISHED
        episode.is_published = True
        episode.publish_date = now
        episode.save(update_fields=["status", "is_published", "publish_date"])
        logger.info(f"Published scheduled episode: {episode.title}")

        from apps.notifications.tasks import send_new_episode_notification
        send_new_episode_notification.delay(str(episode.id))

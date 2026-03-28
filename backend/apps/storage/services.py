import logging
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


class StorageService:
    """
    Abstraction layer for file storage operations.
    Supports local filesystem and S3-compatible backends transparently
    through Django's storage API.
    """

    @classmethod
    def upload_audio(cls, file_obj, podcast_slug, filename=None):
        """
        Upload an audio file to storage.
        Returns the storage path (relative) of the saved file.
        """
        if not filename:
            ext = os.path.splitext(file_obj.name)[1] or ".mp3"
            filename = f"{uuid.uuid4().hex}{ext}"

        storage_path = f"episodes/audio/{podcast_slug}/{filename}"
        saved_path = default_storage.save(storage_path, file_obj)
        logger.info(f"Audio uploaded: {saved_path} ({file_obj.size} bytes)")
        return saved_path

    @classmethod
    def upload_image(cls, file_obj, category="covers", filename=None):
        """
        Upload an image file (cover art, avatar, etc.).
        Returns the storage path.
        """
        if not filename:
            ext = os.path.splitext(file_obj.name)[1] or ".jpg"
            filename = f"{uuid.uuid4().hex}{ext}"

        storage_path = f"images/{category}/{filename}"
        saved_path = default_storage.save(storage_path, file_obj)
        logger.info(f"Image uploaded: {saved_path}")
        return saved_path

    @classmethod
    def delete_file(cls, file_path):
        """Delete a file from storage."""
        if not file_path:
            return False
        try:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                logger.info(f"File deleted: {file_path}")
                return True
            logger.warning(f"File not found for deletion: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return False

    @classmethod
    def get_file_url(cls, file_path):
        """Get the public URL for a stored file."""
        if not file_path:
            return None
        try:
            return default_storage.url(file_path)
        except Exception as e:
            logger.error(f"Failed to get URL for {file_path}: {e}")
            return None

    @classmethod
    def get_file_size(cls, file_path):
        """Get the size of a stored file in bytes."""
        if not file_path:
            return 0
        try:
            return default_storage.size(file_path)
        except Exception:
            return 0

    @classmethod
    def file_exists(cls, file_path):
        """Check if a file exists in storage."""
        if not file_path:
            return False
        return default_storage.exists(file_path)

    @classmethod
    def get_user_storage_usage(cls, user):
        """Calculate total storage used by a user across all their podcasts."""
        from apps.episodes.models import Episode
        from django.db.models import Sum

        total = (
            Episode.objects.filter(podcast__owner=user)
            .aggregate(total=Sum("file_size"))["total"]
        ) or 0
        return total

    @classmethod
    def check_storage_quota(cls, user, additional_bytes=0):
        """
        Check if user has enough storage quota for an upload.
        Returns (has_space: bool, remaining_bytes: int).
        """
        current_usage = cls.get_user_storage_usage(user)
        remaining = user.storage_limit - current_usage
        has_space = remaining >= additional_bytes
        return has_space, max(0, remaining)

    @classmethod
    def generate_presigned_upload_url(cls, file_path, content_type="audio/mpeg", expires=3600):
        """
        Generate a pre-signed URL for direct-to-S3 uploads.
        Only works with S3-compatible storage backends.
        """
        if not getattr(settings, "USE_S3", False):
            return None

        try:
            import boto3
            from botocore.config import Config

            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
                endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
                config=Config(signature_version="s3v4"),
            )

            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": file_path,
                    "ContentType": content_type,
                },
                ExpiresIn=expires,
            )
            return presigned_url

        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    @classmethod
    def cleanup_orphaned_files(cls):
        """
        Find and remove files in storage that are not referenced
        by any database record. Run periodically as a maintenance task.
        """
        from apps.episodes.models import Episode

        orphaned = []
        audio_dir = "episodes/audio/"

        try:
            dirs, files = default_storage.listdir(audio_dir)
            db_files = set(
                Episode.objects.exclude(audio_file="")
                .values_list("audio_file", flat=True)
            )

            for filename in files:
                full_path = os.path.join(audio_dir, filename)
                if full_path not in db_files:
                    orphaned.append(full_path)

            for path in orphaned:
                cls.delete_file(path)

            logger.info(f"Cleaned up {len(orphaned)} orphaned audio files.")

        except Exception as e:
            logger.error(f"Orphan cleanup failed: {e}")

        return len(orphaned)

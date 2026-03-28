import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class PodcastCategory(models.Model):
    """iTunes-compatible podcast category."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE,
        blank=True, null=True, related_name="subcategories",
    )
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class name")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "podcast_categories"
        ordering = ["order", "name"]
        verbose_name_plural = "Podcast categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PodcastTag(models.Model):
    """Tags for podcast discovery."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        db_table = "podcast_tags"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Podcast(models.Model):
    """Core podcast model."""

    class Language(models.TextChoices):
        EN = "en", _("English")
        ES = "es", _("Spanish")
        FR = "fr", _("French")
        DE = "de", _("German")
        PT = "pt", _("Portuguese")
        JA = "ja", _("Japanese")
        ZH = "zh", _("Chinese")
        KO = "ko", _("Korean")
        AR = "ar", _("Arabic")
        HI = "hi", _("Hindi")
        OTHER = "other", _("Other")

    class ContentRating(models.TextChoices):
        CLEAN = "clean", _("Clean")
        EXPLICIT = "explicit", _("Explicit")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="podcasts",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(max_length=5000)
    short_description = models.CharField(max_length=300, blank=True)

    cover_image = models.ImageField(
        upload_to="podcasts/covers/%Y/%m/", blank=True, null=True,
    )
    banner_image = models.ImageField(
        upload_to="podcasts/banners/%Y/%m/", blank=True, null=True,
    )

    category = models.ForeignKey(
        PodcastCategory, on_delete=models.SET_NULL,
        blank=True, null=True, related_name="podcasts",
    )
    tags = models.ManyToManyField(PodcastTag, blank=True, related_name="podcasts")

    language = models.CharField(
        max_length=10, choices=Language.choices, default=Language.EN,
    )
    content_rating = models.CharField(
        max_length=10, choices=ContentRating.choices, default=ContentRating.CLEAN,
    )
    website = models.URLField(max_length=500, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    copyright_text = models.CharField(max_length=300, blank=True)

    is_published = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    publish_date = models.DateTimeField(blank=True, null=True)

    # Statistics (denormalized for performance)
    total_episodes = models.PositiveIntegerField(default=0)
    total_subscribers = models.PositiveIntegerField(default=0)
    total_plays = models.BigIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.00,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "podcasts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "is_published"]),
            models.Index(fields=["category"]),
            models.Index(fields=["-total_subscribers"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Podcast.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.author_name:
            self.author_name = self.owner.display_name or self.owner.email
        super().save(*args, **kwargs)


class PodcastSubscription(models.Model):
    """Tracks user subscriptions to podcasts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="subscriptions",
    )
    notify_new_episodes = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "podcast_subscriptions"
        unique_together = ["user", "podcast"]
        ordering = ["-subscribed_at"]
        indexes = [
            models.Index(fields=["user", "podcast"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.podcast.title}"

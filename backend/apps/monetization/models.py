import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.podcasts.models import Podcast
from apps.episodes.models import Episode


class SponsorDeal(models.Model):
    """Sponsorship deal for a podcast."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PROPOSED = "proposed", _("Proposed")
        ACTIVE = "active", _("Active")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    class AdType(models.TextChoices):
        PRE_ROLL = "pre_roll", _("Pre-Roll")
        MID_ROLL = "mid_roll", _("Mid-Roll")
        POST_ROLL = "post_roll", _("Post-Roll")
        HOST_READ = "host_read", _("Host-Read")
        CUSTOM = "custom", _("Custom Integration")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="sponsor_deals",
    )
    sponsor_name = models.CharField(max_length=200)
    sponsor_email = models.EmailField(blank=True)
    sponsor_website = models.URLField(max_length=500, blank=True)
    sponsor_logo = models.ImageField(
        upload_to="sponsors/logos/", blank=True, null=True,
    )

    ad_type = models.CharField(
        max_length=15, choices=AdType.choices, default=AdType.MID_ROLL,
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFT,
    )

    # Financial
    rate_per_episode = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
    )
    total_episodes = models.PositiveIntegerField(
        default=1, help_text="Number of episodes in the deal",
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    episodes_delivered = models.PositiveIntegerField(default=0)

    # Duration
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    # Script
    talking_points = models.TextField(
        blank=True, help_text="Sponsor talking points or script",
    )
    promo_code = models.CharField(max_length=50, blank=True)
    tracking_url = models.URLField(max_length=500, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sponsor_deals"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sponsor_name} -> {self.podcast.title} ({self.get_status_display()})"

    @property
    def revenue_earned(self):
        return self.rate_per_episode * self.episodes_delivered

    @property
    def is_complete(self):
        return self.episodes_delivered >= self.total_episodes


class Donation(models.Model):
    """One-time donations (tips) from listeners to podcasters."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="donations_made",
    )
    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="donations",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    message = models.TextField(max_length=500, blank=True)
    is_anonymous = models.BooleanField(default=False)

    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING,
    )
    stripe_payment_id = models.CharField(max_length=100, blank=True)
    stripe_charge_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "donations"
        ordering = ["-created_at"]

    def __str__(self):
        donor_name = "Anonymous" if self.is_anonymous else (self.donor or "Guest")
        return f"{donor_name} -> {self.podcast.title}: ${self.amount}"


class PremiumContent(models.Model):
    """Premium/exclusive content for paid subscribers."""

    class ContentType(models.TextChoices):
        EPISODE = "episode", _("Premium Episode")
        BONUS = "bonus", _("Bonus Content")
        EARLY_ACCESS = "early_access", _("Early Access")
        AD_FREE = "ad_free", _("Ad-Free Version")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="premium_content",
    )
    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE,
        blank=True, null=True, related_name="premium_versions",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(max_length=2000, blank=True)
    content_type = models.CharField(
        max_length=15, choices=ContentType.choices, default=ContentType.EPISODE,
    )

    # Pricing
    price = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.00,
        help_text="Price for individual purchase. 0 = subscriber-only.",
    )
    is_subscriber_only = models.BooleanField(
        default=True, help_text="Only accessible to paid subscribers",
    )

    # Media
    audio_file = models.FileField(
        upload_to="premium/audio/%Y/%m/", blank=True,
    )
    duration = models.PositiveIntegerField(default=0)

    is_published = models.BooleanField(default=False)
    publish_date = models.DateTimeField(blank=True, null=True)
    total_purchases = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "premium_content"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[Premium] {self.title} ({self.podcast.title})"

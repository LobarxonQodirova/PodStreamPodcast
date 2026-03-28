import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager supporting email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Email address is required"))
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with role-based access for PodStream."""

    class Role(models.TextChoices):
        LISTENER = "listener", _("Listener")
        PODCASTER = "podcaster", _("Podcaster")
        ADMIN = "admin", _("Admin")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=150, unique=True, blank=True, null=True,
    )
    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.LISTENER,
        db_index=True,
    )
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=1000, blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True, null=True)
    website = models.URLField(max_length=300, blank=True)
    twitter_handle = models.CharField(max_length=50, blank=True)

    # Podcaster-specific fields
    is_verified_podcaster = models.BooleanField(default=False)
    podcaster_since = models.DateTimeField(blank=True, null=True)
    storage_used = models.BigIntegerField(
        default=0, help_text=_("Storage used in bytes")
    )
    storage_limit = models.BigIntegerField(
        default=5 * 1024 * 1024 * 1024,  # 5 GB default
        help_text=_("Storage limit in bytes"),
    )

    # Notification preferences
    email_on_new_episode = models.BooleanField(default=True)
    email_on_comment = models.BooleanField(default=True)
    email_on_subscription = models.BooleanField(default=True)
    email_digest_weekly = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.display_name or self.email

    @property
    def is_podcaster(self):
        return self.role in (self.Role.PODCASTER, self.Role.ADMIN)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def storage_used_mb(self):
        return round(self.storage_used / (1024 * 1024), 2)

    @property
    def storage_remaining(self):
        return max(0, self.storage_limit - self.storage_used)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email.split("@")[0]
            # Ensure uniqueness
            base = self.username
            counter = 1
            while User.objects.filter(username=self.username).exclude(pk=self.pk).exists():
                self.username = f"{base}{counter}"
                counter += 1
        super().save(*args, **kwargs)

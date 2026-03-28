"""
Production-specific Django settings for PodStream.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Only JSON renderer in production
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
)

# Stricter throttling
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "60/hour",
    "user": "600/hour",
}

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")  # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)  # noqa: F405
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)  # noqa: F405
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@podstream.com")  # noqa: F405

# Sentry integration
SENTRY_DSN = config("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
    )

# Production logging
LOGGING["handlers"]["file"] = {  # noqa: F405
    "class": "logging.handlers.RotatingFileHandler",
    "filename": LOG_DIR / "podstream.log",  # noqa: F405
    "maxBytes": 10 * 1024 * 1024,  # 10 MB
    "backupCount": 10,
    "formatter": "verbose",
}
LOGGING["root"]["handlers"] = ["console", "file"]  # noqa: F405
LOGGING["loggers"]["apps"]["handlers"] = ["console", "file"]  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "WARNING"  # noqa: F405

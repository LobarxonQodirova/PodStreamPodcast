"""
Development-specific Django settings for PodStream.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Enable browsable API in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# Relax throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "1000/hour",
    "user": "10000/hour",
}

# CORS: allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Email backend: print to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable HTTPS requirements
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Django Debug Toolbar (optional)
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
except ImportError:
    pass

# Shorter Celery task timeouts for dev
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240

LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
}

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "healthcheck",
    "events",
    "tickets",
    "sync",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

def env(*names, default=None):
    """Return the value of the first set environment variable among `names`."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DATABASE_NAME", "DB_NAME", default="events_aggregator"),
        "USER": env("POSTGRES_USERNAME", "DB_USER", default="events_aggregator"),
        "PASSWORD": env("POSTGRES_PASSWORD", "DB_PASSWORD", default="events_aggregator"),
        "HOST": env("POSTGRES_HOST", "DB_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", "DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "core.pagination.EventsPageNumberPagination",
    "PAGE_SIZE": 20,
}

# --- Events Provider API ---
EVENTS_PROVIDER_BASE_URL = os.environ.get("EVENTS_PROVIDER_BASE_URL", "")
EVENTS_PROVIDER_API_KEY = os.environ.get("EVENTS_PROVIDER_API_KEY", "")


CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "sqla+postgresql://{user}:{password}@{host}:{port}/{name}".format(
        user=env("POSTGRES_USERNAME", "DB_USER", default="events_aggregator"),
        password=env("POSTGRES_PASSWORD", "DB_PASSWORD", default="events_aggregator"),
        host=env("POSTGRES_HOST", "DB_HOST", default="localhost"),
        port=env("POSTGRES_PORT", "DB_PORT", default="5432"),
        name=env("POSTGRES_DATABASE_NAME", "DB_NAME", default="events_aggregator"),
    ),
)
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "0") == "1"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    "synchronize-events-daily": {
        "task": "sync.tasks.synchronize_events_task",
        "schedule": 60 * 60 * 24,  # раз в сутки
    },
}

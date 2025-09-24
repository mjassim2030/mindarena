"""
Django settings for mindarena project.
"""

from pathlib import Path
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.getenv("DEBUG", "1").lower() in {"1", "true", "yes", "on"}

ALLOWED_HOSTS = (
    os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost")
    .replace(" ", "")
    .split(",")
)

# If behind a proxy doing TLS termination, you may want:
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF trusted origins (comma-separated env)
_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [u for u in _csrf.replace(" ", "").split(",") if u] or []
if DEBUG:
    # Helpful defaults for local dev
    CSRF_TRUSTED_ORIGINS += ["http://127.0.0.1:8000", "http://localhost:8000"]

# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "channels",

    # Local
    "main_app",
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

ROOT_URLCONF = "mindarena.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Project-level templates folder (keep app templates too via APP_DIRS=True)
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.static",
            ],
        },
    },
]

# -----------------------------------------------------------------------------
# ASGI / Channels
# -----------------------------------------------------------------------------
ASGI_APPLICATION = "mindarena.asgi.application"
WSGI_APPLICATION = "mindarena.wsgi.application"

# Robust Redis selection:
# - If REDIS_URL is a real URL -> use it
# - elif CHANNELS_REDIS is truthy -> use local redis://127.0.0.1:6379/0
# - else -> fall back to in-memory (single-process dev only)
def _is_url(u: str) -> bool:
    try:
        pr = urlparse(u)
        return pr.scheme in {"redis", "rediss", "unix"} and (bool(pr.netloc) or pr.scheme == "unix")
    except Exception:
        return False

RAW_REDIS_URL = (os.getenv("REDIS_URL") or "").strip()
USE_REDIS_FLAG = os.getenv("CHANNELS_REDIS", "0").lower() in {"1", "true", "yes", "on"}

if _is_url(RAW_REDIS_URL):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [RAW_REDIS_URL]},
        }
    }
elif USE_REDIS_FLAG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": ["redis://127.0.0.1:6379/0"]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
USE_POSTGRES = os.getenv("DB_ENGINE", "sqlite").lower() in {"postgres", "postgresql", "psql"}

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "mindarena"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -----------------------------------------------------------------------------
# Password validation
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# i18n / TZ
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static & Media
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]            # project-level static during dev
STATIC_ROOT = BASE_DIR / "staticfiles"              # collectstatic target (prod)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"                     # for uploaded images (quiz questions)

# -----------------------------------------------------------------------------
# Auth redirects
# -----------------------------------------------------------------------------
LOGIN_URL = "login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# -----------------------------------------------------------------------------
# Misc
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

import os
import sys
from pathlib import Path
from decouple import config
import dj_database_url
import logging

# ───────────────────────────────
# 📁 BASE DIRECTORY
# ───────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ───────────────────────────────
# 🔐 SECURITY
# ───────────────────────────────
SECRET_KEY = config("SECRET_KEY", default='fallback-secret-key-for-dev')
DEBUG = config("DEBUG", default=False, cast=bool)

# ALLOWED_HOSTS — Render-friendly setup
DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "email-assistt.onrender.com",
]

# Render dynamically injects this for your service domain
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default=",".join(DEFAULT_ALLOWED_HOSTS)).split(",")

# Ensure Render domain is added
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# CSRF trusted origins (Render production)
CSRF_TRUSTED_ORIGINS = []
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if not host.startswith("127.")]

# ───────────────────────────────
# 📦 INSTALLED APPS
# ───────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "inbox",  # Your app
    "rest_framework",
    "django_extensions",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]
SITE_ID = 1

# ───────────────────────────────
# 🧱 MIDDLEWARE
# ───────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # For static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ───────────────────────────────
# 🌐 URL + WSGI
# ───────────────────────────────
ROOT_URLCONF = "email_assistant.urls"
WSGI_APPLICATION = "email_assistant.wsgi.application"

# ───────────────────────────────
# 📐 TEMPLATES
# ───────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ───────────────────────────────
# 🛢 DATABASE (Render uses DATABASE_URL)
# ───────────────────────────────
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default="sqlite:///" + str(BASE_DIR / "db.sqlite3")),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=not DEBUG,
    )
}

# ───────────────────────────────
# 🔒 PASSWORD VALIDATORS
# ───────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ───────────────────────────────
# 🌍 I18N
# ───────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ───────────────────────────────
# 📁 STATIC / MEDIA FILES
# ───────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ───────────────────────────────
# 🔑 AUTHENTICATION
# ───────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = None

# Google OAuth
try:
    SOCIALACCOUNT_PROVIDERS = {
        "google": {
            "APP": {
                "client_id": config("GOOGLE_CLIENT_ID", default=""),
                "secret": config("GOOGLE_CLIENT_SECRET", default=""),
                "key": "",
            }
        }
    }
except Exception as e:
    logging.getLogger(__name__).error(f"OAuth config failed: {e}")

# ───────────────────────────────
# 🔐 COOKIE + SESSION
# ───────────────────────────────
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
else:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# ───────────────────────────────
# 🤖 GEMINI API (optional)
# ───────────────────────────────
GEMINI_API_KEY = config("GEMINI_API_KEY", default=None)
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-1.5-flash")

# ───────────────────────────────
# 🧩 REST FRAMEWORK
# ───────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# ───────────────────────────────
# 📧 EMAIL CONFIG (optional)
# ───────────────────────────────
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# ───────────────────────────────
# 🧪 ENVIRONMENT VALIDATION
# ───────────────────────────────
def validate_env():
    required_vars = {
        "GOOGLE_CLIENT_ID": "Google OAuth Client ID",
        "GOOGLE_CLIENT_SECRET": "Google OAuth Client Secret",
        "GEMINI_API_KEY": "Gemini API Key",
    }
    missing = [f"{k} ({v})" for k, v in required_vars.items() if not config(k, default=None)]
    if missing:
        msg = "Missing required environment variables: " + ", ".join(missing)
        if DEBUG:
            print(f"⚠️  {msg}", file=sys.stderr)
        else:
            logging.getLogger(__name__).error(msg)
            if "GOOGLE_CLIENT_ID" in [k.split()[0] for k in missing]:
                raise EnvironmentError(msg)

validate_env()

# ───────────────────────────────
# 📦 CACHING (optional)
# ───────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
        "TIMEOUT": 300,
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
            "CULL_FREQUENCY": 3,
        },
        "KEY_PREFIX": "email_assistant",
        "VERSION": 1,
    }
}

# ───────────────────────────────
# 📊 LOGGING
# ───────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "inbox": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

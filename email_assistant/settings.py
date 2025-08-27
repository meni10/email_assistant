import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url

# --------------------------------------------------------------------
# BASE DIRECTORY
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------
# SECURITY
# --------------------------------------------------------------------
# Use environment variables with fallback to decouple config
SECRET_KEY = os.environ.get('SECRET_KEY', config("SECRET_KEY", default='fallback-secret-key-for-development'))
DEBUG = os.environ.get('DEBUG', config("DEBUG", default='False')) == 'True'

# Allow all hosts in production, specific hosts in development
if DEBUG:
    ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost").split(",")
else:
    ALLOWED_HOSTS = ['*']  # Allow all in production

# --------------------------------------------------------------------
# APPLICATIONS
# --------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles", 
    "inbox",  # Your app
    'django_extensions',  # For additional Django management tools
    'rest_framework',
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]
SITE_ID = 1

# --------------------------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ADD THIS FOR RENDER
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --------------------------------------------------------------------
# URLS / WSGI
# --------------------------------------------------------------------
ROOT_URLCONF = "email_assistant.urls"
WSGI_APPLICATION = "email_assistant.wsgi.application"

# --------------------------------------------------------------------
# TEMPLATES
# --------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # global templates dir
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

# --------------------------------------------------------------------
# DATABASE
# --------------------------------------------------------------------
# Use the database URL from environment variable (Render provides DATABASE_URL)
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///' + str(BASE_DIR / 'db.sqlite3')),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --------------------------------------------------------------------
# PASSWORD VALIDATION
# --------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------
# INTERNATIONALIZATION
# --------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------
# STATIC FILES (CSS, JS, Images)
# --------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Only add STATICFILES_DIRS if the directory exists
static_dir = BASE_DIR / "static"
if static_dir.exists():
    STATICFILES_DIRS = [static_dir]
else:
    STATICFILES_DIRS = []

# Media files configuration
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# --------------------------------------------------------------------
# DEFAULT PRIMARY KEY FIELD TYPE
# --------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------
# AUTHENTICATION (Allauth / Google Login)
# --------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # default
    "allauth.account.auth_backends.AuthenticationBackend",  # allauth
]
LOGIN_REDIRECT_URL = "/"     # change to '/inbox/' if you want dashboard directly
LOGOUT_REDIRECT_URL = "/"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID"),
            "secret": config("GOOGLE_CLIENT_SECRET"),
            "key": ""
        }
    }
}

# --------------------------------------------------------------------
# GOOGLE OAUTH: Allow HTTP in DEBUG
# --------------------------------------------------------------------
if DEBUG:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# --------------------------------------------------------------------
# GEMINI
# --------------------------------------------------------------------
GEMINI_API_KEY = config("GEMINI_API_KEY", default=None)
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-1.5-flash")
if DEBUG and GEMINI_API_KEY:
    print("✅ Gemini API Key loaded successfully")
elif DEBUG:
    print("⚠️  GEMINI_API_KEY not found in .env")

# --------------------------------------------------------------------
# SESSIONS (Database-backed)
# --------------------------------------------------------------------
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Set this to False if running locally (HTTP)
if not DEBUG:
    SESSION_COOKIE_SECURE = True  # Use HTTPS in production
    CSRF_COOKIE_SECURE = True
else:
    SESSION_COOKIE_SECURE = False  # Disable in dev
    CSRF_COOKIE_SECURE = False

SESSION_SAVE_EVERY_REQUEST = True

# --------------------------------------------------------------------
# REST FRAMEWORK
# --------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",  # allow API without login
    ],
}

# If using React frontend for login
LOGIN_URL = None

# --------------------------------------------------------------------
# LOGGING
# --------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'WARNING',  # Change from INFO to WARNING to reduce verbosity
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',  # Keep detailed logs in a file
            'class': 'logging.FileHandler',
            'filename': 'email_assistant.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'inbox': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# --------------------------------------------------------------------
# CACHE
# --------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # Default timeout in seconds
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # Maximum number of entries to store
            'CULL_FREQUENCY': 3,  # The fraction of entries to cull when MAX_ENTRIES is reached
        },
        'KEY_PREFIX': 'email_assistant',  # Prefix for all cache keys
        'VERSION': 1,  # Default version number for cache keys
    }
}
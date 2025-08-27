import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url
import logging
import sys

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

# More robust ALLOWED_HOSTS configuration
DEFAULT_ALLOWED_HOSTS = "127.0.0.1,localhost,email-assistt.onrender.com"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).split(",")

# If we're in production, add additional security settings
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Add CSRF trusted origins for production
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'https://email-assistt.onrender.com',
    ]
    if RENDER_EXTERNAL_HOSTNAME:
        CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

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
        ssl_require=not DEBUG,  # Require SSL in production
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
# Add compression and caching for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# Ensure static directory exists
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir.mkdir(exist_ok=True)
STATICFILES_DIRS = [static_dir]

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
LOGOUT_REDIRECT_URL = "/"    # Ensure logout redirects to home page

# Google OAuth configuration with better error handling
try:
    SOCIALACCOUNT_PROVIDERS = {
        "google": {
            "APP": {
                "client_id": config("GOOGLE_CLIENT_ID"),
                "secret": config("GOOGLE_CLIENT_SECRET"),
                "key": ""
            }
        }
    }
    # Test if the credentials are available
    if not config("GOOGLE_CLIENT_ID") or not config("GOOGLE_CLIENT_SECRET"):
        raise ValueError("Google OAuth credentials are not configured")
except Exception as e:
    # Log the error but don't crash the application
    logger = logging.getLogger(__name__)
    logger.error(f"Google OAuth configuration error: {str(e)}")
    # Use empty configuration to prevent crashes
    SOCIALACCOUNT_PROVIDERS = {
        "google": {
            "APP": {
                "client_id": "",
                "secret": "",
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
try:
    GEMINI_API_KEY = config("GEMINI_API_KEY", default=None)
    GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-1.5-flash")
    
    if DEBUG and GEMINI_API_KEY:
        print("✅ Gemini API Key loaded successfully")
    elif DEBUG:
        print("⚠️  GEMINI_API_KEY not found in .env")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Gemini API configuration error: {str(e)}")
    GEMINI_API_KEY = None
    GEMINI_MODEL = "gemini-1.5-flash"

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
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
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

# --------------------------------------------------------------------
# EMAIL CONFIGURATION
# --------------------------------------------------------------------
EMAIL_BACKEND = config('EMAIL_BACKEND', 
                      default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# --------------------------------------------------------------------
# VALIDATION FOR REQUIRED ENVIRONMENT VARIABLES
# --------------------------------------------------------------------
def validate_environment_variables():
    """Validate that required environment variables are set"""
    required_vars = {
        'GOOGLE_CLIENT_ID': 'Google OAuth Client ID',
        'GOOGLE_CLIENT_SECRET': 'Google OAuth Client Secret',
        'GEMINI_API_KEY': 'Gemini API Key',
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not config(var, default=None):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        if DEBUG:
            print(f"WARNING: {error_msg}", file=sys.stderr)
        else:
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
        
        # In production, we might want to raise an exception for critical variables
        if not DEBUG and 'GOOGLE_CLIENT_ID' in [v.split(' ')[0] for v in missing_vars]:
            # Google OAuth is critical for this app
            raise EnvironmentError(error_msg)

# Validate environment variables when settings are loaded
validate_environment_variables()
import os
import ssl
import sys

import environ
import sentry_sdk
from django_log_formatter_ecs import ECSFormatter
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

APP_ENV = env.str("APP_ENV", default="notset")

# TODO: Change this to use env setting from vault
ALLOWED_HOSTS = "*"

VCAP_SERVICES = env.json("VCAP_SERVICES", default={})

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mail.apps.MailConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "conf.middleware.HawkSigningMiddleware",
]

ROOT_URLCONF = "conf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = "conf.wsgi.application"


# Database https://docs.djangoproject.com/en/2.1/ref/settings/#databases
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {"default": env.db()}

CHIEF_SOURCE_SYSTEM = env("CHIEF_SOURCE_SYSTEM", default="ILBDOTI")

# TODO: Rename these email settings
INCOMING_EMAIL_PASSWORD = env("INCOMING_EMAIL_PASSWORD", default="")
INCOMING_EMAIL_HOSTNAME = env("INCOMING_EMAIL_HOSTNAME", default="")
INCOMING_EMAIL_USER = env("INCOMING_EMAIL_USER", default="")
INCOMING_EMAIL_POP3_PORT = env("INCOMING_EMAIL_POP3_PORT", default=None)

# Used to validate sender details
HMRC_TO_DIT_EMAIL_HOSTNAME = env("HMRC_TO_DIT_EMAIL_HOSTNAME", default="")
HMRC_TO_DIT_EMAIL_USER = env("HMRC_TO_DIT_EMAIL_USER", default="")

OUTGOING_EMAIL_USER = env("OUTGOING_EMAIL_USER")

# TODO: Revisit when implementing ICMSLST-1837
# These 6 EMAIL_* settings are NOT Django default email backend settings.
EMAIL_PASSWORD = env("EMAIL_PASSWORD")
EMAIL_HOSTNAME = env("EMAIL_HOSTNAME")
EMAIL_USER = env("EMAIL_USER")
EMAIL_POP3_PORT = env("EMAIL_POP3_PORT")
EMAIL_SMTP_PORT = env("EMAIL_SMTP_PORT")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

MAILHOG_URL = env.str("MAILHOG_URL", default="http://localhost:8025")

EMAIL_AWAITING_REPLY_TIME = env.int("EMAIL_AWAITING_REPLY_TIME", default=3600)

LICENSE_POLL_INTERVAL = env.int("LICENSE_POLL_INTERVAL", default=300)

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = env.bool("USE_TZ", default=True)

_log_level = env.str("LOG_LEVEL", default="INFO")
if "test" not in sys.argv:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {"format": "{asctime} {levelname} {message}", "style": "{"},
            "ecs_formatter": {"()": ECSFormatter},
        },
        "handlers": {
            "stdout": {"class": "logging.StreamHandler", "formatter": "simple"},
            "ecs": {"class": "logging.StreamHandler", "formatter": "ecs_formatter"},
        },
        "root": {"handlers": ["stdout", "ecs"], "level": _log_level.upper()},
    }
else:
    LOGGING = {"version": 1, "disable_existing_loggers": True}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"

# HAWK
HAWK_AUTHENTICATION_ENABLED = env.bool("HAWK_AUTHENTICATION_ENABLED", default=True)
HAWK_RECEIVER_NONCE_EXPIRY_SECONDS = 60
HAWK_ALGORITHM = "sha256"

# TODO: Change to icms (will require change in ICMS codebase)
LITE_API_ID = "lite-api"
ICMS_API_URL = env("ICMS_API_URL", default="http://web:8080/")
LITE_API_REQUEST_TIMEOUT = 60  # Maximum time, in seconds, to wait between bytes of a response

HAWK_CREDENTIALS = {
    LITE_API_ID: {
        "id": LITE_API_ID,
        "key": env("LITE_API_HAWK_KEY"),
        "algorithm": HAWK_ALGORITHM,
    },
}

# Sentry
if env.str("SENTRY_DSN", ""):
    sentry_sdk.init(
        dsn=env.str("SENTRY_DSN"),
        environment=env.str("SENTRY_ENVIRONMENT"),
        integrations=[DjangoIntegration()],
        send_default_pii=True,
    )
    SENTRY_ENABLED = True
else:
    SENTRY_ENABLED = False

# Application Performance Monitoring
if env.str("ELASTIC_APM_SERVER_URL", ""):
    ELASTIC_APM = {
        "SERVICE_NAME": env.str("ELASTIC_APM_SERVICE_NAME", default="lite-hmrc"),
        "SECRET_TOKEN": env.str("ELASTIC_APM_SECRET_TOKEN"),
        "SERVER_URL": env.str("ELASTIC_APM_SERVER_URL"),
        "ENVIRONMENT": env.str("SENTRY_ENVIRONMENT"),
        "DEBUG": DEBUG,
    }
    INSTALLED_APPS.append("elasticapm.contrib.django")

# Azure email connection settings.
AZURE_AUTH_CLIENT_ID = env.str("AZURE_AUTH_CLIENT_ID")
AZURE_AUTH_CLIENT_SECRET = env.str("AZURE_AUTH_CLIENT_SECRET")
AZURE_AUTH_TENANT_ID = env.str("AZURE_AUTH_TENANT_ID")

# Celery / Redis config
if "redis" in VCAP_SERVICES:
    REDIS_URL = VCAP_SERVICES["redis"][0]["credentials"]["uri"]
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
else:
    REDIS_URL = env.str("REDIS_URL", default="redis://redis:6379")

CELERY_BROKER_URL = REDIS_URL

# Explicit paths to celery tasks.
CELERY_IMPORTS = [
    "mail.icms.tasks",
]


# used in drop_all_tables command
ALLOW_DISASTROUS_DATA_DROPS_NEVER_ENABLE_IN_PROD = env.bool(
    "ALLOW_DISASTROUS_DATA_DROPS_NEVER_ENABLE_IN_PROD", default=False
)

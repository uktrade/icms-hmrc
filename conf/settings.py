import os
import ssl
import sys

import sentry_sdk
from django_log_formatter_ecs import ECSFormatter
from sentry_sdk.integrations.django import DjangoIntegration

from conf.env import env

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.django_secret_key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.debug

APP_ENV = env.app_env

ALLOWED_HOSTS = env.allowed_hosts

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
    "whitenoise.middleware.WhiteNoiseMiddleware",
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

DATABASES = env.database_config

CHIEF_SOURCE_SYSTEM = env.chief_source_system

# TODO: Rename these email settings
# POP3 email settings (to fetch emails from HMRC)
INCOMING_EMAIL_HOSTNAME = env.incoming_email_hostname
INCOMING_EMAIL_USER = env.incoming_email_user  # Also used to send licenceData
INCOMING_EMAIL_POP3_PORT = env.incoming_email_pop3_port

# Azure OAUTH2 email connection settings
AZURE_AUTH_CLIENT_ID = env.azure_auth_client_id
AZURE_AUTH_CLIENT_SECRET = env.azure_auth_client_secret
AZURE_AUTH_TENANT_ID = env.azure_auth_tenant_id

# Used to validate sender details
HMRC_TO_DIT_EMAIL_HOSTNAME = env.hmrc_to_dit_email_hostname
HMRC_TO_DIT_EMAIL_USER = env.hmrc_to_dit_email_user

# Receiver email address
OUTGOING_EMAIL_USER = env.outgoing_email_user

# TODO: Support console backend in tests / replace mailhog?
# DJANGO EMAIL SMTP SETTINGS used to send emails to HMRC from ICMS
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_PORT = env.django_email_port
EMAIL_HOST = env.django_email_host
EMAIL_HOST_USER = env.django_email_host_user
EMAIL_HOST_PASSWORD = env.django_email_host_password
EMAIL_USE_TLS = env.django_email_use_tls
EMAIL_USE_SSL = False
EMAIL_TIMEOUT = None

USE_LEGACY_EMAIL_CODE = env.use_legacy_email_code

MAILHOG_URL = env.mailhog_url

EMAIL_AWAITING_REPLY_TIME = env.email_awaiting_reply_time

LICENSE_POLL_INTERVAL = env.license_poll_interval

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
USE_TZ = env.use_tz

_log_level = env.log_level

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
STATIC_ROOT = os.path.join(BASE_DIR, "static/")

# HAWK
HAWK_AUTHENTICATION_ENABLED = env.hawk_authentication_enabled
HAWK_RECEIVER_NONCE_EXPIRY_SECONDS = 60
HAWK_ALGORITHM = "sha256"

ICMS_API_ID = "icms-api"
ICMS_API_URL = env.icms_api_url
ICMS_API_REQUEST_TIMEOUT = 60  # Maximum time, in seconds, to wait between bytes of a response

HAWK_CREDENTIALS = {
    ICMS_API_ID: {
        "id": ICMS_API_ID,
        "key": env.icms_api_hawk_key,
        "algorithm": HAWK_ALGORITHM,
    },
}

# Sentry
if env.sentry_dsn:
    sentry_sdk.init(
        dsn=env.sentry_dsn,
        environment=env.sentry_environment,
        integrations=[DjangoIntegration()],
        send_default_pii=True,
    )
    SENTRY_ENABLED = True
else:
    SENTRY_ENABLED = False

# Application Performance Monitoring
if env.elastic_apm_server_url:
    ELASTIC_APM = {
        "SERVICE_NAME": env.elastic_apm_service_name,
        "SECRET_TOKEN": env.elastic_apm_secret_token,
        "SERVER_URL": env.elastic_apm_server_url,
        "ENVIRONMENT": env.sentry_environment,
        "DEBUG": DEBUG,
    }
    INSTALLED_APPS.append("elasticapm.contrib.django")

# Celery / Redis config
REDIS_URL = env.redis_url

# Set use_SSL as we are deployed to CF or DBT Platform
if REDIS_URL not in [env.local_redis_url, ""]:
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}


CELERY_BROKER_URL = REDIS_URL

# Explicit paths to celery tasks.
CELERY_IMPORTS = [
    "mail.tasks",
]

# used in drop_all_tables command
ALLOW_DISASTROUS_DATA_DROPS_NEVER_ENABLE_IN_PROD = (
    env.allow_disastrous_data_drops_never_enable_in_prod
)

# Setting for faking licence reply from HMRC
ICMS_FAKE_HMRC_REPLY: str = env.icms_fake_hmrc_reply

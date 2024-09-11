import os

import dj_database_url
from dbt_copilot_python.database import database_url_from_env
from dbt_copilot_python.network import setup_allowed_hosts
from dbt_copilot_python.utility import is_copilot
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .cf_env import CloudFoundryEnvironment


class DBTPlatformEnvironment(BaseSettings):
    """Class holding all environment variables for ICMS-HMRC.

    Instance attributes are matched to environment variables by name (ignoring case).
    e.g. DBTPlatformEnvironment.app_env loads and validates the APP_ENV environment variable.
    """

    model_config = SettingsConfigDict(
        env_prefix="HMRC_",
        extra="ignore",
        validate_default=False,
    )

    # Build step doesn't have "HMRC_" prefix
    build_step: bool = Field(alias="build_step", default=False)

    # DBT Platform environment variables
    # Redis env vars
    celery_broker_url: str = Field(alias="celery_broker_url", default="")

    # Rest of environment variables
    django_secret_key: str
    allowed_hosts: list[str] = ["*"]
    debug: bool = False
    app_env: str = "not_set"
    chief_source_system: str = "ILBDOTI"
    use_tz: bool = True
    log_level: str = "INFO"

    # Hawk Envs
    hawk_authentication_enabled: bool = True
    icms_api_hawk_key: str = ""
    icms_api_url: str = "http://caseworker:8080/"

    # POP3 mail settings
    incoming_email_hostname: str = ""
    incoming_email_user: str = ""
    incoming_email_pop3_port: str = "995"

    # Azure OAUTH2 email connection settings
    azure_auth_client_id: str = ""
    azure_auth_client_secret: str = ""
    azure_auth_tenant_id: str = ""

    # Used to validate sender details
    hmrc_to_dit_email_hostname: str = ""
    hmrc_to_dit_email_user: str = ""

    # Receiver email address
    outgoing_email_user: str = ""

    # DJANGO EMAIL SMTP SETTINGS used to send emails to HMRC from ICMS
    django_email_port: str = ""
    django_email_host: str = ""
    django_email_host_user: str = ""
    django_email_host_password: str = ""
    django_email_use_tls: bool = True

    # Used to determine which email sending code to use.
    use_legacy_email_code: bool = True

    mailhog_url: str = "http://localhost:8025"

    email_awaiting_reply_time: int = 3600

    license_poll_interval: int = 300

    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = Field(alias="sentry_environment", default="")

    # Elactic AMP
    elastic_apm_server_url: str = ""
    elastic_apm_service_name: str = "icms-hmrc"
    elastic_apm_secret_token: str = ""

    # Redis settings
    local_redis_url: str = "redis://redis:6379"

    icms_fake_hmrc_reply: str = "accept"

    @computed_field  # type: ignore[misc]
    @property
    def allowed_hosts_list(self) -> list[str]:
        if self.build_step:
            return self.allowed_hosts

        # Makes an external network request so only call when running on DBT Platform
        return setup_allowed_hosts(self.allowed_hosts)

    @computed_field  # type: ignore[misc]
    @property
    def database_config(self) -> dict:
        if self.build_step:
            return {"default": {}}

        return {
            "default": dj_database_url.config(default=database_url_from_env("DATABASE_CREDENTIALS"))
        }

    @computed_field  # type: ignore[misc]
    @property
    def redis_url(self) -> str:
        if self.build_step:
            return ""

        return self.celery_broker_url


if is_copilot():
    if "BUILD_STEP" in os.environ:
        # When building use a fake value for the django_secret_key
        # Everything else has a default value.
        env: DBTPlatformEnvironment | CloudFoundryEnvironment = DBTPlatformEnvironment(
            django_secret_key="FAKE_SECRET_KEY"  # nosec B106
        )
    else:
        # When deployed read values from environment variables
        env = DBTPlatformEnvironment()  # type:ignore[call-arg]
else:
    # Cloud Foundry environment
    env = CloudFoundryEnvironment()  # type:ignore[call-arg]

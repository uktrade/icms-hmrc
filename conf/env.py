import os
from typing import Annotated, Any

import dj_database_url
from dbt_copilot_python.database import database_url_from_env
from dbt_copilot_python.network import setup_allowed_hosts
from dbt_copilot_python.utility import is_copilot
from pydantic import BaseModel, ConfigDict, PostgresDsn, TypeAdapter, computed_field
from pydantic.functional_validators import PlainValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentBase(BaseSettings):
    """Class holding all environment variables for ICMS-HMRC.

    Instance attributes are matched to environment variables by name (ignoring case).
    e.g. DBTPlatformEnvironment.app_env loads and validates the APP_ENV environment variable.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        validate_default=False,
    )

    django_secret_key: str
    icms_allowed_hosts: list[str] = ["*"]
    debug: bool = False
    app_env: str = "not_set"
    chief_source_system: str = "ILBDOTI"
    use_tz: bool = True
    log_level: str = "INFO"

    # Hawk Envs
    hawk_authentication_enabled: bool = True
    icms_api_hawk_key: str = ""

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

    icms_api_url: str = "http://caseworker:8080/"

    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = ""

    # Elactic AMP
    elastic_apm_server_url: str = ""
    elastic_apm_service_name: str = "icms-hmrc"
    elastic_apm_secret_token: str = ""

    # Redis settings
    local_redis_url: str = "redis://redis:6379"

    allow_disastrous_data_drops_never_enable_in_prod: bool = False

    icms_fake_hmrc_reply: str = "accept"


# Convert the database_url to a PostgresDsn instance
def validate_postgres_dsn_str(val) -> PostgresDsn:
    return TypeAdapter(PostgresDsn).validate_python(val)


CFPostgresDSN = Annotated[PostgresDsn, PlainValidator(validate_postgres_dsn_str)]


class VCAPServices(BaseModel):
    model_config = ConfigDict(extra="ignore")

    postgres: list[dict[str, Any]]
    redis: list[dict[str, Any]]


class VCAPApplication(BaseModel):
    model_config = ConfigDict(extra="ignore")

    application_id: str
    application_name: str
    application_uris: list[str]
    cf_api: str
    limits: dict[str, Any]
    name: str
    organization_id: str
    organization_name: str
    space_id: str
    uris: list[str]


class CloudFoundryEnvironment(EnvironmentBase):
    database_url: CFPostgresDSN

    # Cloud Foundry Environment Variables
    vcap_services: VCAPServices | None = None
    vcap_application: VCAPApplication | None = None

    @computed_field  # type: ignore[misc]
    @property
    def allowed_hosts(self) -> list[str]:
        return self.icms_allowed_hosts

    @computed_field  # type: ignore[misc]
    @property
    def database_config(self) -> dict:
        return {"default": dj_database_url.parse(str(self.database_url))}

    @computed_field  # type: ignore[misc]
    @property
    def redis_url(self) -> str:
        if self.vcap_services:
            return self.vcap_services.redis[0]["credentials"]["uri"]

        return self.local_redis_url


class DBTPlatformEnvironment(EnvironmentBase):
    build_step: bool = False

    # Redis env vars
    celery_broker_url: str = ""

    @computed_field  # type: ignore[misc]
    @property
    def allowed_hosts(self) -> list[str]:
        if self.build_step:
            return self.icms_allowed_hosts

        # Makes an external network request so only call when running on DBT Platform
        return setup_allowed_hosts(self.icms_allowed_hosts)

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
    # Cloud Foundry environemnt
    env = CloudFoundryEnvironment()  # type:ignore[call-arg]

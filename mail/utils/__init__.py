from django.conf import settings


def get_app_env() -> str:
    if settings.APP_ENV == "notset":
        raise ValueError("APP_ENV has not been set")

    return settings.APP_ENV


def is_production_environment() -> bool:
    return get_app_env() == "production"

import json
import logging
from json.decoder import JSONDecodeError

import sentry_sdk

ALLOWED_FILE_MIMETYPES = ["application/octet-stream", "text/plain"]


logger = logging.getLogger(__name__)


def read_file(file_path: str, mode: str = "r", encoding: str = None):
    with open(file_path, mode=mode, encoding=encoding) as f:
        return f.read()


def get_country_id(country):
    try:
        if type(country) == dict:
            country_code = country["id"]
        else:
            country_code = json.loads(country)["id"]
        # skip territory code, if exists
        return country_code.split("-")[0]
    except (TypeError, JSONDecodeError):
        return country.split("-")[0]


def log_to_sentry(message, extra=None, level="info"):
    extra = extra or {}
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level=level)

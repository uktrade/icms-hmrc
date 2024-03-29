"""
Wrapper for Requests HTTP Library.
HAWK signs requests and verifies responses.
"""

import logging
from json import dumps as serialize

import requests  # noqa
from django.conf import settings
from django.core.cache import cache
from mohawk import Sender
from mohawk.exc import AlreadyProcessed

from conf.authentication import hawk_authentication_enabled


class RequestExceptionError(Exception):
    """Exceptions to raise when sending requests."""


def get(url, headers=None, hawk_credentials=None, timeout=None):
    return make_request(
        "GET", url, headers=headers, hawk_credentials=hawk_credentials, timeout=timeout
    )


def post(url, data, headers=None, hawk_credentials=None, timeout=None):
    return make_request(
        "POST", url, data=data, headers=headers, hawk_credentials=hawk_credentials, timeout=timeout
    )


def put(url, data, headers=None, hawk_credentials=None, timeout=None):
    return make_request(
        "PUT", url, data=data, headers=headers, hawk_credentials=hawk_credentials, timeout=timeout
    )


def delete(url, headers=None, hawk_credentials=None, timeout=None):
    return make_request(
        "DELETE", url, headers=headers, hawk_credentials=hawk_credentials, timeout=timeout
    )


def make_request(method, url, data=None, headers=None, hawk_credentials=None, timeout=None):
    headers = headers or {}  # If no headers are supplied, default to an empty dictionary
    headers["content-type"] = "application/json"

    if hawk_authentication_enabled():
        if not hawk_credentials:
            raise RequestExceptionError(
                "'hawk_credentials' must be specified when 'HAWK_AUTHENTICATION_ENABLED' is 'True'"
            )

        sender = get_hawk_sender(method, url, data, hawk_credentials)
        headers["hawk-authentication"] = sender.request_header

        response = send_request(method, url, data=data, headers=headers, timeout=timeout)
        verify_api_response(sender, response)
    else:
        response = send_request(method, url, data=data, headers=headers, timeout=timeout)

    return response


def send_request(method, url, data=None, headers=None, timeout=None):
    try:
        response = requests.request(method, url, json=data, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        raise RequestExceptionError(f"Timeout exceeded when sending request to '{url}'")
    except requests.exceptions.RequestException as exc:
        raise RequestExceptionError(
            f"An unexpected error occurred when sending request to '{url}' -> {type(exc).__name__}: {exc}"
        )

    return response


def get_hawk_sender(method, url, data, credentials):
    content = serialize(data) if data else data
    credentials = settings.HAWK_CREDENTIALS.get(credentials)

    return Sender(
        credentials,
        url,
        method,
        content=content,
        content_type="application/json",
        seen_nonce=_seen_nonce,
    )


def verify_api_response(sender, response):
    try:
        sender.accept_response(
            response.headers["server-authorization"],
            content=response.content,
            content_type=response.headers["Content-Type"],
        )
    except Exception as exc:  # noqa
        logging.warning("Unable to authenticate response from %s", response.url)

        if "server-authorization" not in response.headers:
            logging.warning(
                "'server_authorization' missing in header from response %s; Probable HAWK misconfiguration",
                response.url,
            )

        raise exc


def _seen_nonce(access_key_id, nonce, timestamp):
    """
    Returns if the passed access_key_id/nonce combination has been used before
    """

    cache_key = f"hawk:{access_key_id}:{nonce}"

    # cache.add only adds key if it isn't present
    seen_cache_key = not cache.add(
        cache_key, True, timeout=settings.HAWK_RECEIVER_NONCE_EXPIRY_SECONDS
    )

    if seen_cache_key:
        raise AlreadyProcessed(f"Already seen nonce {nonce}")

    return seen_cache_key

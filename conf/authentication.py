import logging

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from mohawk import Receiver
from mohawk.exc import AlreadyProcessed, HawkFail
from rest_framework import authentication

from conf import settings


class HawkOnlyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        """
        Establish that the request has come from an authorised LITE API client
        by checking that the request is correctly Hawk signed
        """

        try:
            hawk_receiver = _authenticate(request)
        except HawkFail as e:
            logging.warning(f"Failed HAWK authentication {e}")
            raise e

        return AnonymousUser(), hawk_receiver


def _authenticate(request):
    """
    Raises a HawkFail exception if the passed request cannot be authenticated
    """

    if settings.HAWK_AUTHENTICATION_ENABLED:
        return Receiver(
            _lookup_credentials,
            request.META["HTTP_HAWK_AUTHENTICATION"],
            # build_absolute_uri() returns 'http' which is incorrect since our clients communicate via https
            request.build_absolute_uri().replace("http", "https"),
            request.method,
            content=request.body,
            content_type=request.content_type,
            seen_nonce=_seen_nonce,
        )


def _seen_nonce(access_key_id, nonce, _):
    """
    Returns if the passed access_key_id/nonce combination has been
    used within settings.HAWK_RECEIVER_NONCE_EXPIRY_SECONDS
    """

    cache_key = f"hawk:{access_key_id}:{nonce}"

    # cache.add only adds key if it isn't present
    seen_cache_key = not cache.add(cache_key, True, timeout=settings.HAWK_RECEIVER_NONCE_EXPIRY_SECONDS)

    if seen_cache_key:
        raise AlreadyProcessed(f"Already seen nonce {nonce}")

    return seen_cache_key


def _lookup_credentials(access_key_id):
    """
    Raises HawkFail if the access key ID cannot be found.
    """

    try:
        credentials = settings.HAWK_CREDENTIALS[access_key_id]
    except KeyError as exc:
        raise HawkFail(f"No Hawk ID of {access_key_id}") from exc

    return {
        "id": access_key_id,
        "algorithm": "sha256",
        **credentials,
    }

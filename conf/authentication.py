import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from mohawk import Receiver
from mohawk.exc import AlreadyProcessed, HawkFail
from rest_framework import authentication, exceptions
from sentry_sdk import capture_exception

logger = logging.getLogger(__name__)


class HawkOnlyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        """Authenticate the request and return a two-tuple of (user, token).

        Establish that the request has come from an authorised LITE API client
        by checking that the request is correctly Hawk signed
        """

        try:
            hawk_receiver = _authenticate(request)
        except HawkFail as e:
            logger.warning("Failed HAWK authentication %s", e)

            raise exceptions.AuthenticationFailed(f"Failed HAWK authentication")

        except Exception as e:
            logger.error("Failed HAWK authentication %s", e)

            if settings.SENTRY_ENABLED:
                capture_exception(e)

            raise exceptions.AuthenticationFailed(f"Failed HAWK authentication")

        return AnonymousUser(), hawk_receiver

    def authenticate_header(self, request):
        return "Hawk"


def _authenticate(request):
    """Raises a HawkFail exception if the passed request cannot be authenticated"""

    url = request.build_absolute_uri()

    if hawk_authentication_enabled():
        return Receiver(
            _lookup_credentials,
            request.META["HTTP_HAWK_AUTHENTICATION"],
            url,
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


def hawk_authentication_enabled() -> bool:
    """Defined as method as you can't override settings.HAWK_AUTHENTICATION_ENABLED correctly in tests.

    Patch this function to get desired behaviour.
    See here for reason:
    https://stackoverflow.com/questions/29367043/unit-testing-django-rest-framework-authentication-at-runtime
    """

    return settings.HAWK_AUTHENTICATION_ENABLED

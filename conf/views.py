import datetime
import logging
import time
from collections.abc import Callable
from http import HTTPStatus

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from mail.enums import MailStatusEnum
from mail.models import LicencePayload, Mail


def check_database() -> bool:
    try:
        Mail.objects.all().exists()

        return True

    except DatabaseError:
        return False


def check_redis() -> bool:
    try:
        cache.set("test_redis_key", "test_redis_value", timeout=1)
    except Exception:
        return False

    return True


def check_unprocessed_payloads() -> bool:
    dt = timezone.now() + datetime.timedelta(seconds=settings.LICENSE_POLL_INTERVAL)

    payload_object_pending = LicencePayload.objects.filter(
        is_processed=False, received_at__lte=dt
    ).first()

    if payload_object_pending:
        logging.error(
            "Payload object has been unprocessed for over %s seconds: %s",
            settings.LICENSE_POLL_INTERVAL,
            payload_object_pending,
        )
        return False

    return True


def check_pending_mail() -> bool:
    dt = timezone.now() - datetime.timedelta(seconds=settings.EMAIL_AWAITING_REPLY_TIME)
    qs = Mail.objects.exclude(status=MailStatusEnum.REPLY_PROCESSED).filter(sent_at__lte=dt)

    pending_mail = list(qs.values_list("id", flat=True))

    if pending_mail:
        logging.error(
            "The following Mail has been pending for over %s seconds: %s",
            settings.EMAIL_AWAITING_REPLY_TIME,
            pending_mail,
        )
        return False

    return True


def get_services_to_check() -> list[Callable[[], bool]]:
    return [check_database, check_redis, check_unprocessed_payloads, check_pending_mail]


PINGDOM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<pingdom_http_custom_check>
    <status>{status}</status>
    <response_time>{response_time}</response_time>
</pingdom_http_custom_check>\n"""

COMMENT_TEMPLATE = "<!--{comment}-->\n"


def health_check(request: HttpRequest) -> HttpResponse:
    t = time.time()

    failed = [check_func.__name__ for check_func in get_services_to_check() if not check_func()]

    t = time.time() - t

    # pingdom can only accept 3 fractional digits
    t_str = "%.3f" % t

    if not failed:
        return HttpResponse(
            PINGDOM_TEMPLATE.format(status="OK", response_time=t_str), content_type="text/xml"
        )
    else:
        body = PINGDOM_TEMPLATE.format(status="FALSE", response_time=t_str)

        for check_name in failed:
            body += COMMENT_TEMPLATE.format(comment=f"The following check failed: {check_name}")

        return HttpResponse(body, status=HTTPStatus.SERVICE_UNAVAILABLE, content_type="text/xml")


def pingdom_healthcheck(request: HttpRequest) -> HttpResponse:
    t = time.time()

    failed = [
        check_func.__name__ for check_func in [check_database, check_redis] if not check_func()
    ]

    t = time.time() - t

    # pingdom can only accept 3 fractional digits
    t_str = "%.3f" % t

    if not failed:
        return HttpResponse(
            PINGDOM_TEMPLATE.format(status="OK", response_time=t_str), content_type="text/xml"
        )
    else:
        body = PINGDOM_TEMPLATE.format(status="FALSE", response_time=t_str)

        for check_name in failed:
            body += COMMENT_TEMPLATE.format(comment=f"The following check failed: {check_name}")

        return HttpResponse(body, status=HTTPStatus.SERVICE_UNAVAILABLE, content_type="text/xml")

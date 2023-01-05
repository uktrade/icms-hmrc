import logging
import urllib.parse
from typing import Optional

from background_task import background
from django.conf import settings
from django.db import transaction

from mail.enums import ChiefSystemEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.builders import build_licence_data_mail, build_request_mail_message_dto
from mail.libraries.lite_to_edifact_converter import EdifactValidationError
from mail.libraries.routing_controller import send, update_mail
from mail.models import LicencePayload, Mail

logger = logging.getLogger(__name__)


LICENCE_DATA_TASK_QUEUE = "licences_updates_queue"


# Send Usage Figures to LITE API
def get_lite_api_url():
    """The URL for the licence usage callback, from the LITE_API_URL setting.

    If the configured URL has no path, use `/licences/hmrc-integration/`.
    """
    url = settings.LITE_API_URL
    components = urllib.parse.urlparse(url)

    if components.path in ("", "/"):
        components = components._replace(path="/licences/hmrc-integration/")
        url = urllib.parse.urlunparse(components)

    return url


# TODO: Come back to deleting this
@background(queue=LICENCE_DATA_TASK_QUEUE, schedule=0)
def send_licence_data_to_hmrc() -> Optional[bool]:
    """django-background-task version of send_licence_data_to_hmrc"""
    return send_licence_data_to_hmrc_shared()


def send_licence_data_to_hmrc_shared() -> Optional[bool]:
    """Sends LITE (or ICMS) licence updates to HMRC.

    This code is shared between two tasks currently:
      - mail/tasks -> def send_licence_data_to_hmrc (django-background-task task)
      - mail/icms/tasks -> def send_licence_data_to_hmrc (celery task)
    """

    source = SourceEnum.ICMS if settings.CHIEF_SOURCE_SYSTEM == ChiefSystemEnum.ICMS else SourceEnum.LITE
    logger.info(f"Sending {source} licence updates to HMRC")

    if Mail.objects.exclude(status=ReceptionStatusEnum.REPLY_SENT).count():
        logger.info(
            "Currently we are either waiting for a reply or next one is ready to be processed,\n"
            "so we cannot send this update now and will be picked up in the next cycle"
        )
        return

    try:
        with transaction.atomic():
            licences = LicencePayload.objects.filter(is_processed=False).select_for_update(nowait=True)

            if not licences.exists():
                logger.info("There are currently no licences to send")
                return

            mail = build_licence_data_mail(licences, source)
            mail_dto = build_request_mail_message_dto(mail)
            licence_references = [licence.reference for licence in licences]
            logger.info(
                "Created Mail [%s] with subject %s from licences [%s]", mail.id, mail_dto.subject, licence_references
            )

            send(mail_dto)
            update_mail(mail, mail_dto)

            licences.update(is_processed=True)
            logger.info("Licence references [%s] marked as processed", licence_references)

    except EdifactValidationError as err:  # noqa
        raise err
    except Exception as exc:  # noqa
        logger.error(
            "An unexpected error occurred when sending %s licence updates to HMRC -> %s",
            source,
            type(exc).__name__,
            exc_info=True,
        )
    else:
        logger.info("Successfully sent %s licences updates in Mail [%s] to HMRC", source, mail.id)
        return True

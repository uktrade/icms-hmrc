import logging
from typing import Optional

from django.db import transaction

from mail.enums import ReceptionStatusEnum, SourceEnum
from mail.libraries.builders import build_licence_data_mail, build_request_mail_message_dto
from mail.libraries.lite_to_edifact_converter import EdifactValidationError
from mail.libraries.routing_controller import send, update_mail
from mail.models import LicencePayload, Mail

logger = logging.getLogger(__name__)


def send_licence_data_to_hmrc_shared() -> Optional[bool]:
    """Sends ICMS licence updates to HMRC.

    Code is used in one place:
      - mail/icms/tasks -> def send_licence_data_to_hmrc (celery task)
    """

    source = SourceEnum.ICMS
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

import logging

from background_task import background
from django.db import transaction

from mail.enums import ReceptionStatusEnum, ReplyStatusEnum
from mail.libraries.builders import build_update_mail
from mail.libraries.data_processors import build_request_mail_message_dto
from mail.libraries.routing_controller import update_mail, check_and_route_emails, send
from mail.models import LicencePayload, Mail

LICENCE_UPDATES_TASK_QUEUE = "licences_updates_queue"
MANAGE_INBOX_TASK_QUEUE = "manage_inbox_queue"


@background(queue=LICENCE_UPDATES_TASK_QUEUE, schedule=0)
def email_lite_licence_updates():
    logging.info("Sending sent LITE licence updates to HMRC")

    if not _is_email_slot_free():
        logging.info("There is currently an update in progress or an email is in flight")
        return

    with transaction.atomic():
        try:
            licences = LicencePayload.objects.filter(is_processed=False).select_for_update(nowait=True)

            if not licences.exists():
                logging.info("There are currently no licence updates to send")
                return

            logging.info("Creating Mail instance for licence updates")
            mail = build_update_mail(licences)

            logging.info(f"Creating EmailMessageDto from Mail [{id}] instance for licence updates")
            mail_dto = build_request_mail_message_dto(mail)

            logging.info(f"Sending Mail [{id}] to HMRC")
            send(mail_dto)

            logging.info(f"Updating Mail [{id}] and licence instances")
            update_mail(mail, mail_dto)
            licences.update(is_processed=True)

            logging.info("Successfully sent LITE licence updates to HMRC")
        except Exception as exc:  # noqa
            logging.error(
                f"An unexpected error occurred when sending LITE licence updates to HMRC -> {type(exc).__name__}: {exc}"
            )


@background(queue=MANAGE_INBOX_TASK_QUEUE, schedule=0)
def manage_inbox_queue():
    logging.info("Polling inbox for updates")

    try:
        check_and_route_emails()
    except Exception as exc:  # noqa
        logging.error(f"An unexpected error occurred when polling inbox for updates -> {type(exc).__name__}: {exc}")


def _is_email_slot_free() -> bool:
    pending_mail = _get_awaiting_mail()
    if pending_mail:
        logging.error(f"The following Mail is pending: {pending_mail}")
        return False

    rejected_mail = _get_rejected_mail()
    if rejected_mail:
        logging.error(f"The following Mail has been rejected: {pending_mail}")
        return False

    return True


def _get_awaiting_mail() -> []:
    return Mail.objects.filter(status=ReceptionStatusEnum.REPLY_PENDING).values_list("id", flat=True)


def _get_rejected_mail() -> []:
    return Mail.objects.filter(
        status=ReceptionStatusEnum.REPLY_SENT, response_data__icontains=ReplyStatusEnum.REJECTED,
    ).values_list("id", flat=True)

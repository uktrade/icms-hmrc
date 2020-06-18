import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from background_task import background
from django.db import transaction

from conf.settings import EMAIL_USER, NOTIFY_USERS
from mail.enums import ReceptionStatusEnum, ReplyStatusEnum
from mail.libraries.builders import build_update_mail
from mail.libraries.data_processors import build_request_mail_message_dto
from mail.libraries.mailbox_service import send_email
from mail.libraries.routing_controller import update_mail, check_and_route_emails, send
from mail.models import LicencePayload, Mail
from mail.servers import MailServer

LICENCE_UPDATES_TASK_QUEUE = "licences_updates_queue"
MANAGE_INBOX_TASK_QUEUE = "manage_inbox_queue"
NOTIFY_USERS_TASK_QUEUE = "notify_users_queue"


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

            mail = build_update_mail(licences)
            mail_dto = build_request_mail_message_dto(mail)
            licence_references = {licences.values_list("reference", flat=True)}
            logging.info(f"Created Mail [{id}] from licences [{licence_references}]")

            send(mail_dto)
            update_mail(mail, mail_dto)
            logging.info(f"Sent Mail [{id}] to HMRC")

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


@background(queue=NOTIFY_USERS_TASK_QUEUE, schedule=0)
def notify_users_of_rejected_mail(mail_id, mail_response_date):
    logging.info(f"Notifying users of rejected Mail [{mail_id}, {mail_response_date}]")

    try:
        multipart_msg = MIMEMultipart()
        multipart_msg["From"] = EMAIL_USER
        multipart_msg["To"] = ",".join(NOTIFY_USERS)
        multipart_msg["Subject"] = f"Mail rejected"
        body = MIMEText(f"Mail [{mail_id}] received at [{mail_response_date}] was rejected")
        multipart_msg.attach(body)

        server = MailServer()
        smtp_connection = server.connect_to_smtp()
        send_email(smtp_connection, multipart_msg)
        server.quit_smtp_connection()
        logging.info(f"Successfully notified users of rejected Mail [{mail_id}, {mail_response_date}]")
    except Exception as exc:  # noqa
        logging.error(
            f"An unexpected error occurred when notifying users of rejected Mail "
            f"[{mail_id}, {mail_response_date}] -> {type(exc).__name__}: {exc}"
        )

        # Raise an exception
        # this will cause the task to be marked as 'Failed' and retried if there are retry attempts left
        raise Exception(f"Failed to notify users of rejected Mail [{mail_id}, {mail_response_date}]")


def _is_email_slot_free() -> bool:
    pending_mail = _get_pending_mail()
    if pending_mail:
        logging.error(f"The following Mail is pending: {pending_mail}")
        return False

    rejected_mail = _get_rejected_mail()
    if rejected_mail:
        logging.error(f"The following Mail has been rejected: {pending_mail}")
        return False

    return True


def _get_pending_mail() -> []:
    return Mail.objects.exclude(status=ReceptionStatusEnum.REPLY_SENT).values_list("id", flat=True)


def _get_rejected_mail() -> []:
    return Mail.objects.filter(
        status=ReceptionStatusEnum.REPLY_SENT, response_data__icontains=ReplyStatusEnum.REJECTED,
    ).values_list("id", flat=True)

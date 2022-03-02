from rest_framework.exceptions import ValidationError
from typing import Callable, List, Tuple, Optional

import logging
from itertools import islice

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.utils import timezone

from mail import enums
from mail.libraries.builders import build_email_message
from mail.libraries.data_processors import (
    serialize_email_message,
    to_email_message_dto_from,
    lock_db_for_sending_transaction,
)
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import (
    select_email_for_sending,
    sort_dtos_by_date,
    check_for_pending_messages,
    publish_queue_status,
)
from mail.libraries.mailbox_service import get_message_iterator
from mail.models import Mail
from mail.servers import MailServer, get_smtp_connection

logger = logging.getLogger(__name__)


def get_spire_to_dit_mailserver() -> MailServer:
    """
    Mailbox that receives emails sent from SPIRE

    These are licenceData and usageReply emails. They are processed by the service and sent to HMRC.
    """
    return MailServer(
        hostname=settings.INCOMING_EMAIL_HOSTNAME,
        user=settings.INCOMING_EMAIL_USER,
        password=settings.INCOMING_EMAIL_PASSWORD,
        pop3_port=settings.INCOMING_EMAIL_POP3_PORT,
    )


def get_hmrc_to_dit_mailserver() -> MailServer:
    """
    Mailbox that receives reply emails from HMRC

    These are licenceReply and usageData emails
    """
    return MailServer(
        hostname=settings.HMRC_TO_DIT_EMAIL_HOSTNAME,
        user=settings.HMRC_TO_DIT_EMAIL_USER,
        password=settings.HMRC_TO_DIT_EMAIL_PASSWORD,
        pop3_port=settings.HMRC_TO_DIT_EMAIL_POP3_PORT,
    )


def get_mock_hmrc_mailserver() -> MailServer:
    return MailServer(
        hostname=settings.MOCK_HMRC_EMAIL_HOSTNAME,
        user=settings.MOCK_HMRC_EMAIL_USER,
        password=settings.MOCK_HMRC_EMAIL_PASSWORD,
        pop3_port=settings.MOCK_HMRC_EMAIL_POP3_PORT,
    )


def get_spire_standin_mailserver() -> MailServer:
    return MailServer(
        hostname=settings.SPIRE_STANDIN_EMAIL_HOSTNAME,
        user=settings.SPIRE_STANDIN_EMAIL_USER,
        password=settings.SPIRE_STANDIN_EMAIL_PASSWORD,
        pop3_port=settings.SPIRE_STANDIN_EMAIL_POP3_PORT,
    )


def check_and_route_emails():
    logger.info("Checking for emails")
    hmrc_to_dit_server = get_hmrc_to_dit_mailserver()
    email_message_dtos = _get_email_message_dtos(hmrc_to_dit_server, number=None)
    email_message_dtos = sort_dtos_by_date(email_message_dtos)
    logging.info("Incoming message dtos sorted by date: %s" % email_message_dtos)

    spire_to_dit_server = get_spire_to_dit_mailserver()
    if hmrc_to_dit_server != spire_to_dit_server:
        # if the config for the return path is different to outgoing mail path
        # then check the return path otherwise don't bother as it will contain the
        # same emails.
        reply_message_dtos = _get_email_message_dtos(spire_to_dit_server)
        reply_message_dtos = sort_dtos_by_date(reply_message_dtos)
        logging.info("Reply message dtos sorted by date: %s" % reply_message_dtos)

        email_message_dtos.extend(reply_message_dtos)

    if not email_message_dtos:
        pending_message = check_for_pending_messages()
        if pending_message:
            logging.info(
                f"Found pending mail ({pending_message.id}) of extract type {pending_message.extract_type} for sending"
            )
            _collect_and_send(pending_message)

        logger.info(f"No new emails found from {hmrc_to_dit_server.user} or {spire_to_dit_server.user}")

        publish_queue_status()

        return

    for email, mark_status in email_message_dtos:
        try:
            logging.info(f"Processing mail with subject {email.subject}")
            serialize_email_message(email)
            mark_status(enums.MailReadStatuses.READ)
        except ValidationError as ve:
            logger.info(f"Marking message {email.subject} as UNPROCESSABLE. {ve.detail}")
            mark_status(enums.MailReadStatuses.UNPROCESSABLE)

    logger.info("Finished checking for emails")

    mail = select_email_for_sending()  # Can return None in the event of in flight or no pending or no reply_received
    if mail:
        logging.info(
            f"Selected mail ({mail.id}) for sending, extract type {mail.extract_type}, current status {mail.status}"
        )
        _collect_and_send(mail)

    publish_queue_status()


def update_mail(mail: Mail, mail_dto: EmailMessageDto):
    """Update status of mail

    'pending' -> 'reply_pending' -> 'reply_received' -> 'reply_sent'
    """
    previous_status = mail.status

    if mail.status == enums.ReceptionStatusEnum.PENDING:
        mail.status = enums.ReceptionStatusEnum.REPLY_PENDING
        if mail.extract_type == enums.ExtractTypeEnum.USAGE_DATA:
            mail.status = enums.ReceptionStatusEnum.REPLY_SENT

        # Update the mail object to record what we sent to destination
        mail.sent_filename = mail_dto.attachment[0]
        mail.sent_data = mail_dto.attachment[1]
        mail.sent_at = timezone.now()
    else:
        mail.status = enums.ReceptionStatusEnum.REPLY_SENT
        # Update the mail object to record what we sent to source
        mail.sent_response_filename = mail_dto.attachment[0]
        mail.sent_response_data = mail_dto.attachment[1]

    logging.info(f"Updating Mail {mail.id} status from {previous_status} => {mail.status}")

    mail.save()


def send(connection: BaseEmailBackend, email_message_dto: EmailMessageDto):
    logging.info("Preparing to send email")
    email = build_email_message(email_message_dto)

    with connection as conn:
        email.connection = conn
        result = email.send()

    return result


def _collect_and_send(mail: Mail):
    from mail.tasks import send_licence_data_to_hmrc

    logger.info(f"Sending Mail [{mail.id}] of extract type {mail.extract_type}")

    message_to_send_dto = to_email_message_dto_from(mail)
    is_locked_by_me = lock_db_for_sending_transaction(mail)

    if not is_locked_by_me:
        logger.info(f"Mail [{mail.id}] is being sent by another thread")

    if message_to_send_dto:
        if message_to_send_dto.receiver != enums.SourceEnum.LITE and message_to_send_dto.subject:
            smtp_connection = get_smtp_connection(enums.SMTPConnection.SPIRE)
            send(smtp_connection, message_to_send_dto)
            update_mail(mail, message_to_send_dto)

            logger.info(
                f"Mail [{mail.id}] routed from [{message_to_send_dto.sender}] to [{message_to_send_dto.receiver}] with subject {message_to_send_dto.subject}"
            )
        else:
            update_mail(mail, message_to_send_dto)

        if (
            message_to_send_dto.receiver == settings.SPIRE_ADDRESS
            and mail.extract_type == enums.ExtractTypeEnum.LICENCE_DATA
        ):
            # Pick up any LITE licence updates once we send a licence update reply email to SPIRE
            # so LITE does not get locked out of the queue by SPIRE
            send_licence_data_to_hmrc(schedule=0)  # noqa


def _get_email_message_dtos(server: MailServer, number: Optional[int] = 3) -> List[Tuple[EmailMessageDto, Callable]]:
    pop3_connection = server.connect_to_pop3()
    emails_iter = get_message_iterator(pop3_connection, server.user)
    if number:
        emails = list(islice(emails_iter, number))
    else:
        emails = list(emails_iter)
    # emails = read_last_three_emails(pop3_connection)
    server.quit_pop3_connection()
    return emails

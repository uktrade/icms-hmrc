import logging
from itertools import islice
from typing import Callable, List, Optional, Tuple

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from conf.settings import SPIRE_ADDRESS
from mail.auth import BasicAuthentication, ModernAuthentication
from mail.enums import ExtractTypeEnum, MailReadStatuses, ReceptionStatusEnum, SourceEnum
from mail.libraries.builders import build_email_message
from mail.libraries.data_processors import (
    lock_db_for_sending_transaction,
    serialize_email_message,
    to_email_message_dto_from,
)
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import (
    check_for_pending_messages,
    publish_queue_status,
    select_email_for_sending,
    sort_dtos_by_date,
)
from mail.libraries.mailbox_service import get_message_iterator
from mail.models import Mail
from mail.servers import MailServer, smtp_send

logger = logging.getLogger(__name__)


def get_spire_to_dit_mailserver() -> MailServer:
    """
    Mailbox that receives emails sent from SPIRE

    These are licenceData and usageReply emails. They are processed by the service and sent to HMRC.
    """
    auth = ModernAuthentication(
        user=settings.INCOMING_EMAIL_USER,
        client_id=settings.AZURE_AUTH_CLIENT_ID,
        client_secret=settings.AZURE_AUTH_CLIENT_SECRET,
        tenant_id=settings.AZURE_AUTH_TENANT_ID,
    )

    return MailServer(
        auth,
        hostname=settings.INCOMING_EMAIL_HOSTNAME,
        pop3_port=settings.INCOMING_EMAIL_POP3_PORT,
    )


def get_hmrc_to_dit_mailserver() -> MailServer:
    """
    Mailbox that receives reply emails from HMRC

    These are licenceReply and usageData emails
    """
    auth = ModernAuthentication(
        user=settings.HMRC_TO_DIT_EMAIL_USER,
        client_id=settings.AZURE_AUTH_CLIENT_ID,
        client_secret=settings.AZURE_AUTH_CLIENT_SECRET,
        tenant_id=settings.AZURE_AUTH_TENANT_ID,
    )

    return MailServer(
        auth,
        hostname=settings.HMRC_TO_DIT_EMAIL_HOSTNAME,
        pop3_port=settings.HMRC_TO_DIT_EMAIL_POP3_PORT,
    )


def get_mock_hmrc_mailserver() -> MailServer:
    auth = BasicAuthentication(
        user=settings.MOCK_HMRC_EMAIL_USER,
        password=settings.MOCK_HMRC_EMAIL_PASSWORD,
    )

    return MailServer(
        auth,
        hostname=settings.MOCK_HMRC_EMAIL_HOSTNAME,
        pop3_port=settings.MOCK_HMRC_EMAIL_POP3_PORT,
    )


def check_and_route_emails():
    logger.info("Checking for emails")
    hmrc_to_dit_server = get_hmrc_to_dit_mailserver()
    email_message_dtos = get_email_message_dtos(hmrc_to_dit_server, number=None)
    email_message_dtos = sort_dtos_by_date(email_message_dtos)
    logger.info("Incoming message dtos sorted by date: %s", email_message_dtos)

    spire_to_dit_server = get_spire_to_dit_mailserver()
    if hmrc_to_dit_server != spire_to_dit_server:
        # if the config for the return path is different to outgoing mail path
        # then check the return path otherwise don't bother as it will contain the
        # same emails.
        reply_message_dtos = get_email_message_dtos(spire_to_dit_server)
        reply_message_dtos = sort_dtos_by_date(reply_message_dtos)
        logger.info("Reply message dtos sorted by date: %s", reply_message_dtos)

        email_message_dtos.extend(reply_message_dtos)

    if not email_message_dtos:
        pending_message = check_for_pending_messages()
        if pending_message:
            logger.info(
                "Found pending mail (%s) of extract type %s for sending",
                pending_message.id,
                pending_message.extract_type,
            )
            _collect_and_send(pending_message)

        logger.info(
            "No new emails found from %s or %s",
            hmrc_to_dit_server.user,
            spire_to_dit_server.user,
        )

        publish_queue_status()

        return

    for email, mark_status in email_message_dtos:
        try:
            logger.info("Processing mail with subject %s", email.subject)
            serialize_email_message(email)
            mark_status(MailReadStatuses.READ)
        except ValidationError as ve:
            logger.info("Marking message %s as UNPROCESSABLE. %s", email.subject, ve.detail)
            mark_status(MailReadStatuses.UNPROCESSABLE)

    logger.info("Finished checking for emails")

    mail = select_email_for_sending()  # Can return None in the event of in flight or no pending or no reply_received
    if mail:
        logger.info(
            "Selected mail (%s) for sending, extract type %s, current status %s",
            mail.id,
            mail.extract_type,
            mail.status,
        )
        _collect_and_send(mail)

    publish_queue_status()


def update_mail(mail: Mail, mail_dto: EmailMessageDto):
    """Update status of mail

    'pending' -> 'reply_pending' -> 'reply_received' -> 'reply_sent'
    """
    previous_status = mail.status

    if mail.status == ReceptionStatusEnum.PENDING:
        mail.status = ReceptionStatusEnum.REPLY_PENDING
        if mail.extract_type == ExtractTypeEnum.USAGE_DATA:
            mail.status = ReceptionStatusEnum.REPLY_SENT

        # Update the mail object to record what we sent to destination
        mail.sent_filename = mail_dto.attachment[0]
        mail.sent_data = mail_dto.attachment[1]
        mail.sent_at = timezone.now()
    else:
        mail.status = ReceptionStatusEnum.REPLY_SENT
        # Update the mail object to record what we sent to source
        mail.sent_response_filename = mail_dto.attachment[0]
        mail.sent_response_data = mail_dto.attachment[1]

    logger.info("Updating Mail %s status from %s => %s", mail.id, previous_status, mail.status)

    mail.save()


def send(email_message_dto: EmailMessageDto):
    logger.info("Preparing to send email")
    message = build_email_message(email_message_dto)
    smtp_send(message)


def _collect_and_send(mail: Mail):
    from mail.tasks import send_licence_data_to_hmrc

    logger.info("Sending Mail [%s] of extract type %s", mail.id, mail.extract_type)

    message_to_send_dto = to_email_message_dto_from(mail)
    is_locked_by_me = lock_db_for_sending_transaction(mail)

    if not is_locked_by_me:
        logger.info("Mail [%s] is being sent by another thread", mail.id)

    if message_to_send_dto:
        if message_to_send_dto.receiver != SourceEnum.LITE and message_to_send_dto.subject:
            send(message_to_send_dto)
            update_mail(mail, message_to_send_dto)

            logger.info(
                "Mail [%s] routed from [%s] to [%s] with subject %s",
                mail.id,
                message_to_send_dto.sender,
                message_to_send_dto.receiver,
                message_to_send_dto.subject,
            )
        else:
            update_mail(mail, message_to_send_dto)

        if message_to_send_dto.receiver == SPIRE_ADDRESS and mail.extract_type == ExtractTypeEnum.LICENCE_DATA:
            # Pick up any LITE licence updates once we send a licence update reply email to SPIRE
            # so LITE does not get locked out of the queue by SPIRE
            send_licence_data_to_hmrc(schedule=0)  # noqa


def get_email_message_dtos(server: MailServer, number: Optional[int] = 3) -> List[Tuple[EmailMessageDto, Callable]]:
    pop3_connection = server.connect_to_pop3()
    emails_iter = get_message_iterator(pop3_connection, server.user)
    if number:
        emails = list(islice(emails_iter, number))
    else:
        emails = list(emails_iter)
    # emails = read_last_three_emails(pop3_connection)
    server.quit_pop3_connection()
    return emails

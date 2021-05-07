import logging
from django.conf import settings
from email.message import Message
from poplib import POP3_SSL, error_proto
from smtplib import SMTP
from typing import Callable, Iterator, Tuple, List

from mail.enums import MailReadStatuses
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import to_mail_message_dto
from mail.models import Mail, MailboxConfig, MailReadStatus


def send_email(smtp_connection: SMTP, message: Message):
    smtp_connection.send_message(message)


def get_message_id(listing_msg: bytes) -> bytes:
    """
    Takes a single line from pop3 LIST command and extracts
    the message id
    :param listing_msg: a line returned from the pop3.list command, e.g. b"2 5353"
    :return: the message id extracted from the input, for the above example: b"2"
    """
    message_id = listing_msg.split()[0]
    return message_id


def get_message_iterator(pop3_connection: POP3_SSL, username: str) -> Iterator[Tuple[EmailMessageDto, Callable]]:
    mails: list
    _, mails, _ = pop3_connection.list()
    mailbox_config, _ = MailboxConfig.objects.get_or_create(username=username)

    mail_message_ids = [get_message_id(m.decode(settings.DEFAULT_ENCODING)) for m in mails]

    # these are mailbox message ids we've seen before
    read_messages = set(
        MailReadStatus.objects.filter(
            mailbox=mailbox_config, status__in=[MailReadStatuses.READ, MailReadStatuses.UNPROCESSABLE]
        ).values_list("message_id", flat=True)
    )

    for message_id in mail_message_ids:
        # only return messages we haven't seen before
        if message_id not in read_messages:
            read_status, _ = MailReadStatus.objects.get_or_create(message_id=message_id, mailbox=mailbox_config)

            def mark_status(status):
                """
                :param status: A choice from `MailReadStatuses.choices`
                """
                read_status.status = status
                read_status.save()

            try:
                m = pop3_connection.retr(message_id)
            except error_proto as err:
                logging.error(f"Unable to RETR message {message_id} in {mailbox_config}: {err}", exc_info=True)
                continue

            try:
                mail_message = to_mail_message_dto(m)
            except ValueError as ve:
                logging.error(f"Unable to convert message {message_id} to DTO in {mailbox_config}: {ve}", exc_info=True)
                mark_status(MailReadStatuses.UNPROCESSABLE)
                continue

            yield mail_message, mark_status


def read_last_message(pop3_connection: POP3_SSL) -> EmailMessageDto:
    _, mails, _ = pop3_connection.list()
    message_id = get_message_id(mails[-1])
    return to_mail_message_dto(pop3_connection.retr(message_id))


def read_last_three_emails(pop3connection: POP3_SSL) -> list:
    _, mails, _ = pop3connection.list()

    reversed_mails = list(reversed(mails))
    last_three_mails = reversed_mails[:3]

    message_ids = [get_message_id(line.decode(settings.DEFAULT_ENCODING)) for line in last_three_mails]

    emails = [pop3connection.retr(message_id) for message_id in message_ids]

    email_message_dtos = []
    for email in emails:
        email_message_dtos.append(to_mail_message_dto(email))

    return email_message_dtos


def find_mail_of(extract_types: List[str], reception_status: str) -> Mail or None:
    try:
        mail = Mail.objects.get(status=reception_status, extract_type__in=extract_types)
    except Mail.DoesNotExist:
        logging.warning(f"Can not find any mail in [{reception_status}] of extract type [{extract_types}]")
        return

    logging.info(f"Found mail in [{reception_status}] of extract type [{extract_types}] ")
    return mail

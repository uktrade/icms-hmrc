import logging
from email.message import Message
from poplib import POP3_SSL
from smtplib import SMTP

from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import to_mail_message_dto
from mail.models import Mail


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


def read_last_message(pop3_connection: POP3_SSL) -> EmailMessageDto:
    _, mails, _ = pop3_connection.list()
    message_id = get_message_id(mails[-1])
    return to_mail_message_dto(pop3_connection.retr(message_id))


def read_last_three_emails(pop3connection: POP3_SSL) -> list:
    _, mails, _ = pop3connection.list()

    reversed_mails = list(reversed(mails))
    last_three_mails = reversed_mails[:3]

    message_ids = [get_message_id(line.decode("utf-8")) for line in last_three_mails]

    emails = [pop3connection.retr(message_id) for message_id in message_ids]

    email_message_dtos = []
    for email in emails:
        email_message_dtos.append(to_mail_message_dto(email))

    return email_message_dtos


def find_mail_of(extract_type: str, reception_status: str) -> Mail or None:
    try:
        mail = Mail.objects.get(status=reception_status, extract_type=extract_type)
    except Mail.DoesNotExist:
        logging.warning("Can not find any mail in [%s] of extract type [%s]" % (reception_status, extract_type))
        return

    logging.info("Found mail in [%s] of extract type [%s] " % (reception_status, extract_type))
    return mail

import logging
from email.message import Message
from poplib import POP3_SSL
from smtplib import SMTP

from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import to_mail_message_dto
from mail.models import Mail


def send_email(smtp_connection: SMTP, message: Message):
    smtp_connection.send_message(message)


def read_last_message(pop3_connection: POP3_SSL) -> EmailMessageDto:
    _, mails, _ = pop3_connection.list()
    return to_mail_message_dto(pop3_connection.retr(len(mails)))


def read_last_three_emails(pop3connection: POP3_SSL) -> list:
    _, mails, _ = pop3connection.list()
    emails = [
        pop3connection.retr(len(mails)),
        pop3connection.retr(len(mails) - 1),
        pop3connection.retr(len(mails) - 2),
    ]

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

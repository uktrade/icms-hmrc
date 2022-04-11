import logging
from email.message import Message
from poplib import POP3_SSL, error_proto
from smtplib import SMTP
from typing import Callable, Iterator, List, Tuple

from django.conf import settings

from mail.enums import MailReadStatuses
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import to_mail_message_dto
from mail.models import Mail, MailboxConfig, MailReadStatus


def send_email(smtp_connection: SMTP, message: Message):
    smtp_connection.send_message(message)


def get_message_id(pop3_connection, listing_msg):
    """
    Takes a single line from pop3 LIST command and extracts
    the message num. Uses the message number further to extract header information
    from which the actual Message-ID is extracted.

    :param pop3_connection: pop3 connection instance
    :param listing_msg: a line returned from the pop3.list command, e.g. b"2 5353"
    :return: the message-id and message_num extracted from the input, for the above example: b"2"
    """
    msg_num = listing_msg.split()[0]

    # retrieves the header information
    # 0 indicates the number of lines of message to be retrieved after the header
    msg_header = pop3_connection.top(msg_num, 0)

    spire_from_address = settings.SPIRE_FROM_ADDRESS.encode("utf-8")
    hmrc_dit_reply_address = settings.HMRC_TO_DIT_REPLY_ADDRESS.encode("utf-8")

    if spire_from_address not in msg_header[1] and hmrc_dit_reply_address not in msg_header[1]:
        logging.warning(
            f"Found mail with message_num {msg_num} that is not from SPIRE ({spire_from_address}) or HMRC ({hmrc_dit_reply_address}), skipping ..."
        )
        return None, msg_num

    message_id = None
    for index, item in enumerate(msg_header[1]):
        hdr_item_fields = item.decode("utf-8").split(" ")
        # message id is of the form b"Message-ID: <963d810e-c573-ef26-4ac0-151572b3524b@email-domail.co.uk>"

        if len(hdr_item_fields) == 2:
            if hdr_item_fields[0].lower() == "message-id:":
                value = hdr_item_fields[1].replace("<", "").replace(">", "")
                message_id = value.split("@")[0]
        elif len(hdr_item_fields) == 1:
            if hdr_item_fields[0].lower() == "message-id:":
                value = msg_header[1][index + 1].decode("utf-8")
                value = value.replace("<", "").replace(">", "").strip(" ")
                message_id = value.split("@")[0]

    logging.info(f"Extracted Message-Id as {message_id} for the message_num {msg_num}")
    return message_id, msg_num


def get_read_messages(mailbox_config):
    return [
        str(m.message_id)
        for m in MailReadStatus.objects.filter(
            mailbox=mailbox_config, status__in=[MailReadStatuses.READ, MailReadStatuses.UNPROCESSABLE]
        )
    ]


def get_message_iterator(pop3_connection: POP3_SSL, username: str) -> Iterator[Tuple[EmailMessageDto, Callable]]:
    mails: list
    _, mails, _ = pop3_connection.list()
    mailbox_config, _ = MailboxConfig.objects.get_or_create(username=username)

    # Check only the last 500 emails
    # Since we don't delete emails from these mailboxes the total number can be very high over a perio
    # and increases the processing time.
    # The mails is a list of message number and size - message number is an increasing value so the
    # latest emails will always be at the end.
    mail_message_ids = [get_message_id(pop3_connection, m.decode(settings.DEFAULT_ENCODING)) for m in mails[-500:]]

    # these are mailbox message ids we've seen before
    read_messages = get_read_messages(mailbox_config)
    logging.info(f"Number of messages READ/UNPROCESSABLE in {mailbox_config.username} are {len(read_messages)}")

    for message_id, message_num in mail_message_ids:
        # only return messages we haven't seen before
        if message_id is not None and message_id not in read_messages:
            read_status, _ = MailReadStatus.objects.get_or_create(
                message_id=message_id, message_num=message_num, mailbox=mailbox_config
            )

            def mark_status(status):
                """
                :param status: A choice from `MailReadStatuses.choices`
                """
                logging.info(
                    f"Marking message_id {message_id} with message_num {message_num} from {read_status.mailbox.username} as {status}"
                )
                read_status.status = status
                read_status.save()

            try:
                m = pop3_connection.retr(message_num)
                logging.info(
                    f"Retrieved message_id {message_id} with message_num {message_num} from {read_status.mailbox.username}"
                )
            except error_proto as err:
                logging.error(
                    f"Unable to RETR message num {message_num} with Message-ID {message_id} in {mailbox_config}: {err}",
                    exc_info=True,
                )
                continue

            try:
                mail_message = to_mail_message_dto(m)
            except ValueError as ve:
                logging.error(
                    f"Unable to convert message num {message_id} with Message-Id {message_id} to DTO in {mailbox_config}: {ve}",
                    exc_info=True,
                )
                mark_status(MailReadStatuses.UNPROCESSABLE)
                continue

            yield mail_message, mark_status


def read_last_message(pop3_connection: POP3_SSL) -> EmailMessageDto:
    _, mails, _ = pop3_connection.list()
    message_id, message_num = get_message_id(pop3_connection, mails[-1])

    try:
        message = pop3_connection.retr(message_num)
    except error_proto as err:
        raise Exception(
            f"Unable to RETR message num {message_num} with Message-ID {message_id}",
        ) from err

    return to_mail_message_dto(message)


def read_last_three_emails(pop3connection: POP3_SSL) -> list:
    _, mails, _ = pop3connection.list()

    reversed_mails = list(reversed(mails))
    last_three_mails = reversed_mails[:3]

    message_ids = [get_message_id(pop3connection, line.decode(settings.DEFAULT_ENCODING)) for line in last_three_mails]

    emails = []
    for message_id, message_num in message_ids:
        try:
            emails.append(pop3connection.retr(message_num))
        except error_proto as err:
            raise Exception(
                f"Unable to RETR message num {message_num} with Message-ID {message_id}",
            ) from err

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

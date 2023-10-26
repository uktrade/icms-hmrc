import dataclasses
import datetime as dt
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.utils import timezone
from unidecode import unidecode

from mail.enums import ExtractTypeEnum
from mail.models import LicenceData, Mail

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class EmailMessageData:
    run_number: int
    sender: str
    receiver: str
    date: dt.datetime
    subject: str
    body: None
    attachment: list[str, str]


def build_request_mail_message_dto(mail: Mail) -> EmailMessageData:
    sender = None
    receiver = None
    attachment = [None, None]
    run_number = 0

    if mail.extract_type == ExtractTypeEnum.LICENCE_DATA:
        sender = settings.INCOMING_EMAIL_USER
        receiver = settings.OUTGOING_EMAIL_USER
        licence_data = LicenceData.objects.get(mail=mail)
        run_number = licence_data.hmrc_run_number
        attachment = [
            _build_sent_filename(mail.edi_filename, run_number),
            _build_sent_file_data(mail.edi_data, run_number),
        ]

    logger.info(
        "Preparing request Mail dto of extract type %s, sender %s, receiver %s with filename %s",
        mail.extract_type,
        sender,
        receiver,
        attachment[0],
    )

    return EmailMessageData(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        date=timezone.now(),
        subject=attachment[0],
        body=None,
        attachment=attachment,
    )


def _build_sent_filename(filename: str, run_number: int) -> str:
    filename = filename.split("_")
    filename[4] = str(run_number)
    return "_".join(filename)


def _build_sent_file_data(file_data: str, run_number: int) -> str:
    file_data_lines = file_data.split("\n", 1)

    file_data_line_1 = file_data_lines[0]
    file_data_line_1 = file_data_line_1.split("\\")
    file_data_line_1[6] = str(run_number)
    file_data_line_1 = "\\".join(file_data_line_1)

    return file_data_line_1 + "\n" + file_data_lines[1]


def build_email_message(email_message_dto: EmailMessageData) -> MIMEMultipart:
    """Build mail message from EmailMessageData.
    :param email_message_dto: the DTO object this mail message is built upon
    :return: a multipart message
    """
    _validate_dto(email_message_dto)

    logger.info("Building email message...")
    file = unidecode(email_message_dto.attachment[1], errors="replace")

    if email_message_dto.attachment[1] != file:
        logger.info(
            "File content different after transliteration\nBefore: %s\nAfter: %s\n",
            email_message_dto.attachment[1],
            file,
        )

    multipart_msg = MIMEMultipart()
    # the SMTP server only allows sending as itself
    multipart_msg["From"] = settings.EMAIL_HOST_USER
    multipart_msg["To"] = email_message_dto.receiver
    multipart_msg["Subject"] = email_message_dto.subject
    multipart_msg["name"] = email_message_dto.subject
    multipart_msg.attach(MIMEText("\n\n", "plain", "iso-8859-1"))
    payload = MIMEApplication(file)
    payload.set_payload(file)
    payload.add_header(
        "Content-Disposition",
        f'attachment; filename="{email_message_dto.attachment[0]}"',
    )
    payload.add_header("Content-Transfer-Encoding", "7bit")
    payload.add_header("name", email_message_dto.subject)
    multipart_msg.attach(payload)
    logger.info("Message headers: %s, Payload headers: %s", multipart_msg.items(), payload.items())
    return multipart_msg


def _validate_dto(email_message_dto):
    if email_message_dto is None:
        raise TypeError("None email_message_dto received!")

    if email_message_dto.attachment is None:
        raise TypeError("None file attachment received!")

import dataclasses
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from unidecode import unidecode_expect_ascii

from mail.enums import ExtractTypeEnum
from mail.models import Mail

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class EmailMessageData:
    receiver: str
    subject: str
    body: None
    attachment: tuple[str, str]


def build_request_mail_message_dto(mail: Mail) -> EmailMessageData:
    if mail.extract_type != ExtractTypeEnum.LICENCE_DATA:
        raise ValueError(
            f"Unable to build EmailMessageData for mail.extract_type: {mail.extract_type}"
        )

    receiver = settings.OUTGOING_EMAIL_USER
    attachment = (mail.edi_filename, mail.edi_data)

    logger.info(
        "Preparing request Mail dto of extract type: %s, receiver: %s with filename: %s",
        mail.extract_type,
        receiver,
        mail.edi_filename,
    )

    return EmailMessageData(
        receiver=receiver,
        subject=mail.edi_filename,
        body=None,
        attachment=attachment,
    )


def build_email_message(email_message_dto: EmailMessageData) -> MIMEMultipart:
    """Build mail message from EmailMessageData.
    :param email_message_dto: the DTO object this mail message is built upon
    :return: a multipart message
    """
    _validate_dto(email_message_dto)

    logger.info("Building email message...")
    # DES23513 section: 12.2.1. - Overview
    # The characters as transferred are in ISO 646 (ASCII).
    file = unidecode_expect_ascii(email_message_dto.attachment[1], errors="replace")

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

    # Attach new line to email body
    # Lite team member suggested this was required for the email to be accepted by HMRC mailserver
    multipart_msg.attach(MIMEText("\n\n", "plain", "iso-8859-1"))

    # Attach file to email
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

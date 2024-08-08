import logging

from django.conf import settings
from django.core.mail import DEFAULT_ATTACHMENT_MIME_TYPE, EmailMessage
from unidecode import unidecode_expect_ascii

from mail.chief.email import EmailMessageData, build_email_message
from mail.servers import smtp_send

logger = logging.getLogger(__name__)


class ChiefEmailMessage(EmailMessage):
    encoding = "ascii"


def send_email_wrapper(email_data: EmailMessageData) -> None:
    """Used to send emails to CHIEF.

    Until after we go live we are preserving the old lite-hmrc email sending code in case the
    new version is not correct.
    """

    if settings.USE_LEGACY_EMAIL_CODE:
        logger.info("Sending email to hmrc using mail.servers.smtp_send")
        message = build_email_message(email_data)
        smtp_send(message)

    else:
        logger.info("Sending email to hmrc using mail.email.send_chief_email")
        # Sends attachment base64 encoded
        count = send_chief_email(email_data)
        # Sends as raw text.
        # count = send_chief_email(email_data, attachment_mimetype="text/plain")

        logger.info("%s emails sent to CHIEF", count)


def send_chief_email(
    email_data: EmailMessageData, attachment_mimetype: str = DEFAULT_ATTACHMENT_MIME_TYPE
) -> int:
    """Send licence data email to CHIEF.

    Returns the number of emails sent.
    """

    # DES23513 section: 12.2.1. - Overview
    # The characters as transferred are in ISO 646 (ASCII).
    file_content = unidecode_expect_ascii(email_data.attachment[1], errors="replace")

    if email_data.attachment[1] != file_content:
        logger.info(
            "File content different after transliteration\nBefore: %s\nAfter: %s\n",
            email_data.attachment[1],
            file_content,
        )

    licence_data_file = (
        # filename
        email_data.attachment[0],
        # content
        file_content,
        # mimetype
        attachment_mimetype,
    )

    mail = ChiefEmailMessage(
        subject=email_data.subject,
        body=email_data.body,
        from_email=settings.EMAIL_HOST_USER,
        to=[email_data.receiver],
        attachments=[licence_data_file],
    )

    return mail.send()

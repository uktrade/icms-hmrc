import logging

from django.utils import timezone

from mail.enums import ReceptionStatusEnum
from mail.libraries.builders import build_email_message
from mail.libraries.email_message_dto import EmailMessageDto
from mail.models import Mail
from mail.servers import smtp_send

logger = logging.getLogger(__name__)


# NEEDED (def send_licence_data_to_hmrc_shared)
def update_mail(mail: Mail, mail_dto: EmailMessageDto):
    """Update status of mail

    'pending' -> 'reply_pending' -> 'reply_received' -> 'reply_sent'
    """
    previous_status = mail.status

    if mail.status == ReceptionStatusEnum.PENDING:
        mail.status = ReceptionStatusEnum.REPLY_PENDING

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


# NEEDED (def send_licence_data_to_hmrc_shared)
def send(email_message_dto: EmailMessageDto):
    logger.info("Preparing to send email")
    message = build_email_message(email_message_dto)
    smtp_send(message)

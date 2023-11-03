import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from mail.chief.email import EmailMessageData
from mail.email.utils import send_email_wrapper
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.models import LicenceData, Mail

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Command to resend an email corresponding to the given hmrc run number

    Arguments:
    hmrc_run_number: The run number used by HMRC to identify this mail.

    Based on hmrc run number the command identifies the relevant LicenceData, Mail instances and
    prepares the mail to be resent. Some assertions are included to ensure the filenames match the
    one that is being resent.

    -------------------------
    When to use this command
    -------------------------
    Below is the only case where this command should be used:

    When a licence_data mail is sent to HMRC successfully from our system but it hasn't reached HMRC.
    In this case we expect status of the mail to be 'reply_pending' and extract_type as 'licence_data'.
    Besides there should be only one instance with this status.
    If the mail sent to HMRC is actually received and accepted by them and if for some reason we need to
    resend again then this command should not be used. That is because once it is accepted by their systems
    sending again with same run number is an error and will be rejected by their systems.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--hmrc_run_number",
            type=str,
            nargs="?",
            help="Run number used by HMRC to identify the mail to be resent",
        )
        parser.add_argument("--dry_run", help="Is it a test run?", action="store_true")

    def handle(self, *args, **options):
        hmrc_run_number = options.pop("hmrc_run_number")
        dry_run = options.pop("dry_run")

        destination = SourceEnum.HMRC
        mail = get_mail_extract(hmrc_run_number)

        if not mail:
            logger.error("hmrc_run_number %s does not belong to Licence data mail", hmrc_run_number)
            return

        if mail.extract_type != ExtractTypeEnum.LICENCE_DATA:
            logger.error("Unexpected extract_type for the mail %s", mail.edi_filename)
            return

        if mail.status != ReceptionStatusEnum.REPLY_PENDING:
            logger.error(
                "Mail is expected to be in 'reply_pending' status but current status is %s",
                mail.status,
            )
            return

        message_to_send_dto = _build_request_mail_message_dto_internal(mail)
        if not dry_run:
            send_email_wrapper(message_to_send_dto)

        logger.info("Mail %s resent to %s successfully", message_to_send_dto.subject, destination)


def get_mail_extract(hmrc_run_number: int) -> Mail | None:
    try:
        licence_data = LicenceData.objects.get(hmrc_run_number=hmrc_run_number)
        return licence_data.mail
    except LicenceData.DoesNotExist:
        logger.info("No licence data instance found for given run number %s", hmrc_run_number)

    return None


def _build_request_mail_message_dto_internal(mail: Mail) -> EmailMessageData:
    if mail.extract_type != ExtractTypeEnum.LICENCE_DATA:
        raise Exception(f"Extract type not supported: {mail.extract_type}")

    sender = settings.EMAIL_HOST_USER
    receiver = settings.OUTGOING_EMAIL_USER
    attachment = [mail.sent_filename, mail.sent_data]

    logger.info(
        "Preparing request Mail dto of extract type %s, sender %s, receiver %s with filename %s",
        mail.extract_type,
        sender,
        receiver,
        attachment[0],
    )

    return EmailMessageData(
        # run_number isn't used when sending the email
        run_number=0,
        sender=sender,
        receiver=receiver,
        date=timezone.now(),
        subject=attachment[0],
        body=None,
        attachment=attachment,
    )

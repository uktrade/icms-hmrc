import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.builders import _build_request_mail_message_dto_internal
from mail.libraries.routing_controller import send
from mail.models import LicenceData, UsageData
from mail.servers import MailServer

logger = logging.getLogger(__name__)


def get_mail_extract(hmrc_run_number):
    licence_data = None
    usage_data = None

    """
    Given run number could be of licence data or usage data so check both types.
    Mostly it will be of licence data as they are more frequent compared to
    usage data so check this first.
    """
    try:
        licence_data = LicenceData.objects.get(hmrc_run_number=hmrc_run_number)
        return licence_data.mail
    except LicenceData.DoesNotExist:
        logger.info("No licence data instance found for given run number %s", hmrc_run_number)

    try:
        usage_data = UsageData.objects.get(hmrc_run_number=hmrc_run_number)
        return usage_data.mail
    except UsageData.DoesNotExist:
        logger.info("No usage data instance found for given run number %s", hmrc_run_number)

    return None


class Command(BaseCommand):
    help = """
    Command to resend an email corresponding to the given hmrc run number

    Arguments:
    hmrc_run_number: The input run number *must* be the run number used by HMRC to identify this mail.
    If the mail has come from SPIRE then their current run number is different from the hmrc run number
    because lite-hmrc translates it when sending it to HMRC. For this reason it is important to use
    HMRC run number as the starting point when resending it.

    Based on hmrc run number the command identifies the relevant LicenceData, Mail instances and
    prepares the mail to be resent. Some assertions are included to ensure the filenames match the
    one that is being resent.

    -------------------------
    When to use this command
    -------------------------
    Below are the only cases where this command should be used,

    Case1: When a licence_data mail is sent to HMRC successfully from our system but it hasn't reached HMRC
    In this case we expect status of the mail to be 'reply_pending' and extract_type as 'licence_data'
    Besides there should be only one instance with this status.
    If the mail sent to HMRC is actually received and accepted by them and if for some reason we need to
    resend again then this command should not be used. That is because once it is accepted by their systems
    sending again with same run number is an error and will be rejected by their systems.

    Case2: When a licence_reply mail is sent to SPIRE successfully from our system but it hasn't reached SPIRE
    In this case we expect status of the mail to be 'reply_sent' and extract_type as 'licence_reply'

    Case3: When a usage_data mail is sent to SPIRE successfully from our system but it hasn't reached SPIRE
    In this case we expect status of the mail to be 'reply_sent' and extract_type as 'usage_data'

    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--hmrc_run_number", type=str, nargs="?", help="Run number used by HMRC to identify the mail to be resent"
        )
        parser.add_argument("--dry_run", help="Is it a test run?", action="store_true")

    def handle(self, *args, **options):
        hmrc_run_number = options.pop("hmrc_run_number")
        dry_run = options.pop("dry_run")

        destination = None
        mail = get_mail_extract(hmrc_run_number)
        if not mail:
            logger.error("Given run number %s does not belong to Licence data or Usage data mail", hmrc_run_number)
            return

        """
        Usually we resend in cases where the mail is initially sent from our system successfully but not received
        by the recipient. This could happen with HMRC in case of licence data mails and with SPIRE in
        case of licence reply mails. Below we check for their expected status and set destination.
        """
        # this is the usual case where we had to resend
        if mail.extract_type == ExtractTypeEnum.LICENCE_DATA:
            destination = SourceEnum.HMRC
            if mail.status != ReceptionStatusEnum.REPLY_PENDING:
                logger.error("Mail is expected to be in 'reply_pending' status but current status is %s", mail.status)
                return
        # this does happen occassionally
        elif mail.extract_type == ExtractTypeEnum.LICENCE_REPLY:
            destination = SourceEnum.SPIRE
            if mail.status != ReceptionStatusEnum.REPLY_SENT:
                logger.error("Mail is expected to be in 'reply_sent' status but current status is %s", mail.status)
                return
        elif mail.extract_type == ExtractTypeEnum.USAGE_DATA:
            destination = SourceEnum.SPIRE
            if mail.status != ReceptionStatusEnum.REPLY_SENT:
                logger.error("Mail is expected to be in 'reply_sent' status but current status is %s", mail.status)
                return
        else:
            logger.error("Unexpected extract_type for the mail %s", mail.edi_filename)
            return

        message_to_send_dto = _build_request_mail_message_dto_internal(mail)
        if not message_to_send_dto:
            logger.error("Unexpected extract_type for the mail %s", mail.edi_filename)
            return

        if not dry_run:
            server = MailServer(
                hostname=settings.EMAIL_HOSTNAME,
                user=settings.EMAIL_USER,
                password=settings.EMAIL_PASSWORD,
                pop3_port=settings.EMAIL_POP3_PORT,
                smtp_port=settings.EMAIL_SMTP_PORT,
            )
            send(server, message_to_send_dto)

        logger.info("Mail %s resent to %s successfully", message_to_send_dto.subject, destination)

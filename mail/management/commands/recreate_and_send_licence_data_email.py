import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from mail.chief.email import build_request_mail_message_dto
from mail.chief.licence_data import create_licence_data_mail
from mail.chief.licence_reply import LicenceReplyProcessor
from mail.email.utils import send_email_wrapper
from mail.enums import MailStatusEnum, SourceEnum
from mail.models import LicenceData

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Command to recreate and send a licence data email to HMRC.

    This command can only be used when we have received a licenceReply from HMRC and the
    mail.status field is set to "reply_partially_processed".

    This command should be run after the bug is fixed that caused the file error in the
    licenceReply file.

    Arguments:
    hmrc_run_number: The run number used by HMRC to identify this mail.
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

        # Get the partially processed mail and licence data object.
        ld = LicenceData.objects.get(hmrc_run_number=hmrc_run_number)

        original_mail = ld.mail
        if original_mail.status != MailStatusEnum.REPLY_PARTIALLY_PROCESSED:
            raise CommandError("This command only works with partially processed mail.")

        # send a new licenceData email for the unprocessed records in the current mail record.
        licences = self._get_unprocessed_payloads(ld)
        mail = create_licence_data_mail(licences, SourceEnum.ICMS)

        mail_dto = build_request_mail_message_dto(mail)

        logger.info(
            "Created Mail [%s] with subject %s from licences [%s]",
            mail.id,
            mail_dto.subject,
            [licence.reference for licence in licences],
        )

        send_email_wrapper(mail_dto)

        # Update the mail object to indicate we are waiting for a reply from HMRC.
        mail.status = MailStatusEnum.REPLY_PENDING
        mail.sent_at = timezone.now()
        mail.save()

        # Archive the original mail now we have sent another licenceData mail
        original_mail.status = MailStatusEnum.REPLY_PROCESSED
        original_mail.save()

    def _get_unprocessed_payloads(self, ld: LicenceData):
        processor = LicenceReplyProcessor.load_from_mail(ld.mail)

        if not processor.reply_file_is_partially_valid():
            raise CommandError(
                "This command only works when resending records from partially valid files."
            )

        licence_payloads = ld.licence_payloads.all()

        # Exclude already accepted licences
        if processor.accepted_licences:
            licence_payloads = licence_payloads.exclude(
                reference__in=[at.transaction_ref for at in processor.accepted_licences]
            )

        # Exclude already rejected licences
        if processor.rejected_licences:
            licence_payloads = licence_payloads.exclude(
                reference__in=[rt.header.transaction_ref for rt in processor.rejected_licences]
            )

        if not licence_payloads.exists():
            raise CommandError("There are no LicencePayloads left to send back to HMRC")

        return licence_payloads

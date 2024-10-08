import dataclasses
from typing import Iterable, List

from django.core.management import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from mail import utils
from mail.chief.licence_data.chiefprotocol import FIELD_SEP, LINE_SEP
from mail.chief.licence_reply import types
from mail.enums import FakeChiefLicenceReplyEnum, MailStatusEnum
from mail.models import LicenceData, LicencePayload, Mail


class Command(BaseCommand):
    """Development command to fake a LicenceReply file.

    It is simulating the work that this task does:
    icms-hmrc/mail/tasks.py -> process_licence_reply_and_usage_emails

    Checks for mail that have been sent to CHIEF
    Processes each line and creates a test reply file.
    Supports one of several outcomes:

    How to run:
    make manage args="dev_fake_licence_reply accept"
    make manage args="dev_fake_licence_reply reject"
    make manage args="dev_fake_licence_reply file_error"
    make manage args="dev_fake_licence_reply unknown_error"
    """

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            dest="outcome",
            default=FakeChiefLicenceReplyEnum.ACCEPT,
            nargs="?",
            type=str,
            choices=FakeChiefLicenceReplyEnum.values,
            help="Licence Reply outcome; accept, reject, random, file_error",
        )

    @transaction.atomic()
    def handle(self, outcome: FakeChiefLicenceReplyEnum, *args, **options):
        self.stdout.write(f"Desired outcome: {outcome}")

        if utils.is_production_environment():
            self.stdout.write("This command is only for development environments")
            return

        # Search for a mail instance that is in REPLY_PENDING
        mail: Mail = (
            Mail.objects.select_for_update().filter(status=MailStatusEnum.REPLY_PENDING).first()
        )

        if not mail:
            self.stdout.write(f"No mail records with {MailStatusEnum.REPLY_PENDING} status")
            return

        self.stdout.write(f"Mail instance found: {mail.id} - {mail.edi_filename}")

        # Use the LicencePayload records to construct a fake LicenceReply file
        ld: LicenceData = mail.licencedata_set.get()
        created_at = timezone.now().strftime("%Y%m%d%H%M")

        data = [
            types.FileHeader(
                source_system="CHIEF",
                destination="ILBDOTI",
                data_id="licenceReply",
                creation_datetime=created_at,
                run_num=ld.hmrc_run_number,
            )
        ]

        counts = {"accept": 0, "reject": 0, "file_error": 0}

        match outcome:
            case FakeChiefLicenceReplyEnum.ACCEPT | FakeChiefLicenceReplyEnum.REJECT:
                func_map = {"accept": get_accepted_transaction, "reject": get_rejected_transaction}

                get_transaction = func_map[outcome]

                for lp in ld.licence_payloads.all():
                    data.extend(get_transaction(lp))

                counts[outcome] = ld.licence_payloads.count()

            case FakeChiefLicenceReplyEnum.FILE_ERROR:
                data.append(
                    types.FileError(
                        code="18", text="Record type 'fileHeader' not recognised", position="99"
                    )
                )
                counts["file_error"] = 1

            case FakeChiefLicenceReplyEnum.UNKNOWN_ERROR:
                self.stdout.write(
                    "Returning without updating mail record to simulate no response from HMRC."
                )
                return

        data.append(
            types.FileTrailer(
                accepted_count=counts["accept"],
                rejected_count=counts["reject"],
                file_error_count=counts["file_error"],
            )
        )

        # Store the fake LicenceReply file and filename (response_filename, response_data)
        licence_reply_filename = f"CHIEF_licenceReply_{ld.hmrc_run_number}_{created_at}"
        licence_reply_file = create_licence_reply_file(data)

        mail.status = MailStatusEnum.REPLY_RECEIVED
        mail.response_filename = licence_reply_filename
        mail.response_data = licence_reply_file
        mail.response_date = timezone.now()
        mail.response_subject = licence_reply_filename
        mail.save()

        self.stdout.write("Successfully faked LicenceReply file from CHIEF.")


def get_accepted_transaction(lp: LicencePayload) -> list:
    return [types.AcceptedTransaction(transaction_ref=lp.reference)]


def get_rejected_transaction(lp: LicencePayload) -> list:
    return [
        types.RejectedTransactionHeader(transaction_ref=lp.reference),
        types.RejectedTransactionError(code="12345", text=f"Fake error message for {lp.reference}"),
        types.RejectedTransactionTrailer(start_record_type="rejected", record_count=3),
    ]


def create_licence_reply_file(licence_reply_lines: List[dataclasses.dataclass]):
    return LINE_SEP.join(
        format_line((line_no, line.record_type) + dataclasses.astuple(line))
        for line_no, line in enumerate(licence_reply_lines, start=1)
    )


def format_line(fields: Iterable) -> str:
    return FIELD_SEP.join(str(f) for f in fields)

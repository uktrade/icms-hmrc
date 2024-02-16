from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from mail.enums import ExtractTypeEnum, MailStatusEnum, SourceEnum
from mail.models import LicenceData, Mail


class Command(BaseCommand):
    help = """Command to seed the LicenceData and Mail models.

    Required so that the first live email will have the correct hmrc_run_number when we go live.
    How to run locally:
    make manage args="seed_licence_data --last-live-run-number=12345"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--last-live-run-number",
            type=int,
            nargs="?",
            help="License reference number of the license payload",
            required=True,
        )

    def handle(self, *args, last_live_run_number: int, **options):
        if LicenceData.objects.exists():
            raise CommandError("Unable to seed LicenceData as it already contains records.")

        self.stdout.write(f"Creating {last_live_run_number} fake LicenceData and Mail records.")

        for i in range(last_live_run_number):
            now = timezone.now()

            fake_mail = Mail.objects.create(
                extract_type=ExtractTypeEnum.LICENCE_DATA,
                status=MailStatusEnum.REPLY_PROCESSED,
                edi_filename="fake_licence_data_filename",
                edi_data="Fake licence_data created in seed_licence_data command",
                sent_at=now,
                response_filename="fake_reply_filename",
                response_data="Fake licence_reply created in seed_licence_data command",
                response_date=now,
                response_subject="Fake response subject",
            )

            LicenceData.objects.create(
                licence_ids="",
                hmrc_run_number=i + 1,
                source=SourceEnum.ICMS,
                mail=fake_mail,
            )

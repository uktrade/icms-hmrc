from django.core.management import BaseCommand
from django.db import transaction
from django.test import override_settings

from mail.chief.email import EmailMessageData
from mail.email.utils import send_email_wrapper


# To run locally: make manage args="check_email_sending --send-to example@email.com"
class Command(BaseCommand):
    """Command to test email sending."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--send-to",
            type=str,
            action="store",
            help="Email address to send email to",
            required=True,
        )

    @transaction.atomic()
    def handle(self, *args, send_to: str, **options):
        mail_dto = EmailMessageData(
            receiver=send_to,
            subject="Test email",
            body=None,
            # Add a few snowmen to test unidecode_expect_ascii text changes.
            attachment=("test_file.txt", "some ☃ test ☃ data"),
        )

        # Send a new email (default mimetype)
        with override_settings(USE_LEGACY_EMAIL_CODE=False):
            send_email_wrapper(mail_dto)

        with override_settings(USE_LEGACY_EMAIL_CODE=True):
            send_email_wrapper(mail_dto)

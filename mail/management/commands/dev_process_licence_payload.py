from django.conf import settings
from django.core.management import BaseCommand

from mail.tasks import send_licence_data_to_hmrc


class Command(BaseCommand):
    """Development command to trigger sending LicenceData payloads to HMRC."""

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write("This command is only for development environments")
            return

        send_licence_data_to_hmrc.now()

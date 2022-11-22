from django.conf import settings
from django.core.management import BaseCommand

from mail.icms import tasks


class Command(BaseCommand):
    """Development command to send licence record data back to ICMS."""

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write("This command is only for development environments")
            return

        tasks.send_licence_data_to_icms()

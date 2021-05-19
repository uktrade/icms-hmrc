from django.conf import settings
from django.core.management.base import BaseCommand

from mail import enums, models
from mail.libraries.mailbox_service import get_message_id
from mail.servers import MailServer


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--mailbox", type=str, nargs="?", help="Email address from which the mails are to be read and mark as read"
        )
        parser.add_argument("--password", type=str, nargs="?", help="Password for the mailbox")
        parser.add_argument("--dry_run", type=str, nargs="?", help="Is it a test run", default="True")

    def handle(self, *args, **options):
        email_user = options.pop("mailbox")
        email_password = options.pop("password")
        dry_run = options.pop("dry_run")

        server = MailServer(
            hostname=settings.EMAIL_HOSTNAME, user=email_user, password=email_password, pop3_port=995, smtp_port=587,
        )
        pop3_connection = server.connect_to_pop3()
        self.stdout.write(self.style.SUCCESS(f"Connected to {email_user}"))

        _, mails, _ = pop3_connection.list()
        self.stdout.write(self.style.SUCCESS(f"Found {len(mails)} in the inbox"))

        mail_message_ids = [get_message_id(pop3_connection, m.decode(settings.DEFAULT_ENCODING)) for m in mails]
        self.stdout.write(
            self.style.SUCCESS(f"List of Message-Id and message numbers for existing mails:\n{mail_message_ids}")
        )

        if dry_run.lower() == "false":
            mailbox_config, _ = models.MailboxConfig.objects.get_or_create(username=email_user)

            for message_id, message_num in mail_message_ids:
                if message_id is None:
                    continue

                read_status, _ = models.MailReadStatus.objects.get_or_create(
                    message_id=message_id, message_num=message_num, mailbox=mailbox_config,
                )
                read_status.status = enums.MailReadStatuses.READ
                read_status.save()
                self.stdout.write(self.style.SUCCESS(f"Message-Id {message_id} marked as Read"))

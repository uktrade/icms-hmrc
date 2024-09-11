import email

from django.conf import settings
from django.core.management import BaseCommand

from mail import tasks
from mail.utils import pop3


# To run locally: make manage args="check_licence_reply_mailbox_connection"
class Command(BaseCommand):
    """Tests read access to mailbox"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--fetch-email",
            help="Fetch the email body / attachments?",
            action="store_true",
            default=False,
        )

    def handle(self, *args, fetch_email: bool, **options):
        auth = tasks.get_licence_reply_mailbox_auth()
        mailbox_hostname = settings.INCOMING_EMAIL_HOSTNAME
        port = settings.INCOMING_EMAIL_POP3_PORT

        with pop3.get_connection(auth, mailbox_hostname, port) as con:
            msg_ids = pop3.list_messages_ids(con)

            self.stdout.write(f"Count of msg_ids: {len(msg_ids)}")

            if fetch_email:
                # Fetch the last three messages
                for m_id in msg_ids[-3:]:
                    self.stdout.write("=" * 80)
                    mail = pop3.get_email(con, m_id)

                    # Test calling this (as it gets called in the task)
                    tasks.check_sender_valid(
                        mail,
                        expected_sender_domain=settings.HMRC_TO_DIT_EMAIL_HOSTNAME,
                        expected_sender_user=settings.HMRC_TO_DIT_EMAIL_USER,
                    )

                    self.stdout.write(f"Message ID: {m_id}")
                    self.print_mail(mail)

    def print_mail(self, mail: email.message.EmailMessage) -> None:
        subject = mail.get("Subject")
        _from = mail.get("From")
        self.stdout.write(f"Subject: {subject}")
        self.stdout.write(f"From: {_from}")
        self.stdout.write(f"From.address: {_from.addresses}")
        self.stdout.write(f"Body: {mail.get_body()}")
        for attach in mail.iter_attachments():
            self.stdout.write(attach.get_filename())

            payload_bytes = attach.get_payload(decode=True)
            self.stdout.write(payload_bytes.decode())

from time import sleep

from django.test import tag

from conf.test_client import LiteHMRCTestClient
from mail.builders import build_text_message
from mail.models import Mail
from mail.scheduling.scheduler import scheduled_job
from mail.servers import MailServer
from mail.services.MailboxService import MailboxService


class EndToEndTest(LiteHMRCTestClient):
    @tag("end-to-end")
    def test_end_to_end_success_licence_update(self):
        # send email to lite from spire
        pop3_port = 995
        smtp_port = 587
        user = "test"
        spire_hostname = "lite-hmrc-spiremail"
        service = MailboxService()
        service.send_email(
            MailServer(
                smtp_port=smtp_port, user=user, hostname=spire_hostname,
            ).connect_to_smtp(),
            build_text_message("test@spire.com", "username@example.com"),
        )
        scheduled_job()
        sleep(6)

        print(Mail.objects.last())

        msg = service.read_last_message(
            MailServer(
                pop3_port=pop3_port,
                user=user,
                password=password,
                hostname=spire_hostname,
            ).connect_to_pop3()
        )

        print(msg)

        self.assertEqual(msg, True)

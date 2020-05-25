from random import randint
from time import sleep

from django.test import tag

from conf.settings import SPIRE_ADDRESS
from conf.test_client import LiteHMRCTestClient
from mail.builders import build_text_message
from mail.models import Mail
from mail.routing_controller import check_and_route_emails
from mail.servers import MailServer
from mail.services.MailboxService import MailboxService


class EndToEndTest(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

    @tag("end-to-end")
    def test_end_to_end_success_licence_update(self):
        file_name = "ILBDOTI_live_CHIEF_licenceUpdate_49543_201902" + str(
            randint(1, 99999)  # nosec
        )

        # send email to lite from spire
        service = MailboxService()
        service.send_email(
            MailServer().connect_to_smtp(),
            build_text_message(
                SPIRE_ADDRESS,
                "username@example.com",
                [file_name, self.licence_usage_file_body],
            ),
        )
        sleep(5)
        check_and_route_emails()
        sleep(5)
        server = MailServer()
        pop3_conn = server.connect_to_pop3()
        last_msg_dto = MailboxService().read_last_message(pop3_conn)
        pop3_conn.quit()

        print("\n\n\n")
        print(last_msg_dto)

        in_mail = Mail.objects.get(edi_filename=file_name)
        self.assertEqual(
            in_mail.edi_filename, file_name,
        )

        print("\n\n\n")
        print(in_mail.__dict__)
        print("\n\n\n")

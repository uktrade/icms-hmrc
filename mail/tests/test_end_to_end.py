from unittest import mock

from django.test import tag
from django.urls import reverse

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.data_processors import serialize_email_message
from mail.libraries.helpers import get_extract_type
from mail.libraries.mailbox_service import read_last_message
from mail.libraries.routing_controller import _collect_and_send
from mail.models import Mail, LicenceUpdate, LicencePayload
from mail.servers import MailServer
from mail.tasks import send_licence_updates_to_hmrc
from mail.tests.libraries.client import LiteHMRCTestClient


class SmtpMock:
    def quit(self):
        pass


class EndToEndTests(LiteHMRCTestClient):
    @staticmethod
    def print_mail(mail):
        print("id", mail.id)
        print("created_at", mail.created_at)
        print("last_submitted_on", mail.last_submitted_on)
        if mail.edi_filename:
            print("edi_filename", mail.edi_filename[0:100])
            print("edi_data", mail.edi_data[0:100])
        print("status", mail.status[:100])
        print("extract_type", mail.extract_type[:100])
        if mail.response_filename:
            print("response_filename", mail.response_filename[0:100])
            print("response_data", mail.response_data[:50])
            print("response_date", mail.response_date)
            print("response_subject", mail.response_subject)
        print("serializer_errors", mail.serializer_errors)
        print("errors", mail.errors)
        print("currently_processing_at", mail.currently_processing_at)
        print("currently_processed_by", mail.currently_processed_by)

    @tag("system-start")
    @tag("end-to-end")
    def test_system_start(self):
        print("\nThis is the system start\n------------------\n")
        count = Mail.objects.count()
        print("Current number of mail objects\t", count)
        if count:
            print("Status of last mail object\t", Mail.objects.last().status)

        server = MailServer()
        pop3_conn = server.connect_to_pop3()

        last_msg_dto = read_last_message(pop3_conn)

        print("\nMessage retrieved:\n----------------")
        print("run number\t", last_msg_dto.run_number)
        print("attachment\t", last_msg_dto.attachment[0])
        print("file\t\t", last_msg_dto.attachment[1][0:150])

        if get_extract_type(last_msg_dto.subject) == "licence_reply":
            mail = Mail(extract_type=ExtractTypeEnum.LICENCE_UPDATE, status=ReceptionStatusEnum.REPLY_PENDING,)
            mail.save()
            lu = LicenceUpdate(
                source=SourceEnum.SPIRE,
                source_run_number=last_msg_dto.run_number,
                hmrc_run_number=last_msg_dto.run_number,
                licence_ids="['GBSIEL/2020/0000001/P', 'GBSIEL/2020/0000001/P']",
                mail=mail,
            )
            lu.save()

        serialize_email_message(last_msg_dto)

        count = Mail.objects.count()
        print("Current number of mail objects\t", count)
        if count:
            print("Status of last mail object\t", Mail.objects.last().status)

        print("\nMail snapshot\n-----------")
        mail = Mail.objects.get()
        self.print_mail(mail)

        _collect_and_send(mail)

        mail = Mail.objects.get()
        self.print_mail(mail)

    @tag("end-to-end")
    @tag("mocked")
    @mock.patch("mail.tasks.send_email")
    def test_send_email_to_hmrc_e2e_mocked(self, send_email):
        send_email.return_value = SmtpMock()
        self.single_siel_licence_payload.is_processed = True

        self.client.post(
            reverse("mail:update_licence"), data=self.licence_payload_json, content_type="application/json"
        )

        send_licence_updates_to_hmrc.now()  # Manually calling background task logic

        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 2)

    @tag("end-to-end")
    def test_send_email_to_hmrc_e2e_non_mocked(self):
        self.client.post(
            reverse("mail:update_licence"), data=self.licence_payload_json, content_type="application/json"
        )

        send_licence_updates_to_hmrc.now()

        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 2)

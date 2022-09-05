from datetime import datetime, timezone
from unittest import mock

from django.conf import settings
from django.core.management import call_command

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.routing_controller import check_and_route_emails
from mail.models import LicenceData, Mail, UsageData
from mail.tests.libraries.client import LiteHMRCTestClient


class LITEHMRCResendEmailTests(LiteHMRCTestClient):
    @mock.patch("mail.libraries.routing_controller.get_spire_to_dit_mailserver")
    @mock.patch("mail.libraries.routing_controller.get_hmrc_to_dit_mailserver")
    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller.get_email_message_dtos")
    def test_resend_licence_data_mail_to_hmrc(
        self,
        email_dtos,
        send_mail,
        mock_get_hmrc_to_dit_mailserver,
        mock_get_spire_to_dit_mailserver,
    ):
        """
        Tests resending of licence data mail to HMRC
        Initially we setup an email and send it to HMRC and this sets the mail is in the
        required status. Now the test executes the management command which resends the email
        """
        source_run_number = 49530
        hmrc_run_number = 49543
        filename = self.licence_data_file_name
        mail_body = self.licence_data_file_body.decode("utf-8")
        pending_mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.PENDING,
            sent_at=datetime.now(timezone.utc),
        )
        LicenceData.objects.create(
            mail=pending_mail,
            source_run_number=source_run_number,
            hmrc_run_number=hmrc_run_number,
            source=SourceEnum.SPIRE,
            licence_ids=f"{source_run_number},{hmrc_run_number}",
        )
        email_dtos.return_value = []
        check_and_route_emails()

        # assert that the pending mail is sent and status updated
        mail = Mail.objects.get(id=pending_mail.id)
        send_mail.assert_called_once()
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_PENDING)

        call_command("resend_email", "--hmrc_run_number", 49543)

        mail_qs = Mail.objects.filter(status=ReceptionStatusEnum.REPLY_PENDING)
        self.assertEqual(mail_qs.count(), 1)
        mail = mail_qs.first()
        self.assertEqual(mail.id, pending_mail.id)
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_PENDING)
        self.assertEqual(mail.extract_type, ExtractTypeEnum.LICENCE_DATA)
        self.assertEqual(send_mail.call_count, 2)

    @mock.patch("mail.libraries.routing_controller.get_spire_to_dit_mailserver")
    @mock.patch("mail.libraries.routing_controller.get_hmrc_to_dit_mailserver")
    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller.get_email_message_dtos")
    def test_resend_licence_reply_mail_to_spire(
        self,
        email_dtos,
        send_mail,
        mock_get_hmrc_to_dit_mailserver,
        mock_get_spire_to_dit_mailserver,
    ):
        source_run_number = 49530
        hmrc_run_number = 49543
        filename = self.licence_reply_file_name
        mail_body = self.licence_reply_file_body.decode("utf-8")
        pending_mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.LICENCE_REPLY,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.REPLY_PENDING,
            sent_at=datetime.now(timezone.utc),
        )
        LicenceData.objects.create(
            mail=pending_mail,
            source_run_number=source_run_number,
            hmrc_run_number=hmrc_run_number,
            source=SourceEnum.SPIRE,
            licence_ids=f"{source_run_number},{hmrc_run_number}",
        )

        email_message_dto = EmailMessageDto(
            run_number=source_run_number,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.SPIRE_ADDRESS,
            body=None,
            date=datetime.now(),
            subject=self.licence_reply_file_name,
            attachment=[
                self.licence_reply_file_name,
                self.licence_reply_file_body,
            ],
            raw_data="qwerty",
        )
        email_dtos.side_effect = [
            [
                (email_message_dto, lambda x: x),
            ],
            [],
        ]

        check_and_route_emails()

        # assert that the pending mail is sent and status updated
        mail = Mail.objects.get(id=pending_mail.id)
        send_mail.assert_called_once()
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_SENT)

        call_command("resend_email", "--hmrc_run_number", 49543)

        mail_qs = Mail.objects.filter(status=ReceptionStatusEnum.REPLY_SENT)
        self.assertEqual(mail_qs.count(), 1)
        mail = mail_qs.first()
        self.assertEqual(mail.id, pending_mail.id)
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_SENT)
        self.assertEqual(mail.extract_type, ExtractTypeEnum.LICENCE_REPLY)
        send_mail.assert_called_once()

    @mock.patch("mail.libraries.routing_controller.get_spire_to_dit_mailserver")
    @mock.patch("mail.libraries.routing_controller.get_hmrc_to_dit_mailserver")
    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller.get_email_message_dtos")
    def test_resend_usage_data_mail_to_spire(
        self,
        email_dtos,
        send_mail,
        mock_get_hmrc_to_dit_mailserver,
        mock_get_spire_to_dit_mailserver,
    ):
        source_run_number = 49530
        hmrc_run_number = 49543
        filename = self.licence_usage_file_name
        mail_body = self.licence_usage_file_body.decode("utf-8")
        pending_mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.USAGE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.PENDING,
            sent_at=datetime.now(timezone.utc),
        )
        UsageData.objects.create(
            mail=pending_mail,
            spire_run_number=source_run_number,
            hmrc_run_number=hmrc_run_number,
            licence_ids=f"{source_run_number},{hmrc_run_number}",
        )

        email_message_dto = EmailMessageDto(
            run_number=source_run_number,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.SPIRE_ADDRESS,
            body=None,
            date=datetime.now(),
            subject=self.licence_usage_file_name,
            attachment=[
                self.licence_usage_file_name,
                self.licence_usage_file_body,
            ],
            raw_data="qwerty",
        )
        email_dtos.side_effect = [
            [
                (email_message_dto, lambda x: x),
            ],
            [],
        ]

        check_and_route_emails()

        # assert that the pending mail is sent and status updated
        mail = Mail.objects.get(id=pending_mail.id)
        send_mail.assert_called_once()
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_SENT)

        call_command("resend_email", "--hmrc_run_number", 49543)

        mail_qs = Mail.objects.filter(status=ReceptionStatusEnum.REPLY_SENT)
        self.assertEqual(mail_qs.count(), 1)
        mail = mail_qs.first()
        self.assertEqual(mail.id, pending_mail.id)
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_SENT)
        self.assertEqual(mail.extract_type, ExtractTypeEnum.USAGE_DATA)
        send_mail.assert_called_once()

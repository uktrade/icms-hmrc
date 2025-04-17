import datetime as dt
from unittest import mock

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils.timezone import make_aware

from mail.chief.email import EmailMessageData
from mail.enums import ExtractTypeEnum, MailStatusEnum, SourceEnum
from mail.models import LicenceData, Mail


class TestResendLicenceDataEmail:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.mail = Mail.objects.create(
            status=MailStatusEnum.REPLY_PENDING,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename="the_licence_data_file",
            edi_data="lovely data",
            sent_at=make_aware(dt.datetime(2024, 1, 1)),
        )

        self.ld = LicenceData.objects.create(
            hmrc_run_number=123, licence_ids="", source=SourceEnum.ICMS, mail=self.mail
        )

    @mock.patch("mail.management.commands.resend_email.send_email_wrapper")
    def test_can_resend_licence_data_email(self, mock_send_email_wrapper):
        call_command("resend_email", hmrc_run_number=self.ld.hmrc_run_number)

        # Check we sent the expected email
        expected_mdo = EmailMessageData(
            receiver=settings.OUTGOING_EMAIL_USER,
            subject=self.mail.edi_filename,
            body=None,
            attachment=(self.mail.edi_filename, self.mail.edi_data),
        )
        mock_send_email_wrapper.assert_called_once_with(expected_mdo)

        # Check the email sent_at date has been updated
        self.mail.refresh_from_db()
        assert self.mail.sent_at.date() == dt.datetime.today().date()

        # Check the hmrc_run_number hasn't changed
        self.ld.refresh_from_db()
        assert self.ld.hmrc_run_number == 123

    def test_invalid_hmrc_run_number(self, capsys):
        call_command("resend_email", hmrc_run_number=999)

        captured = capsys.readouterr()
        assert captured.err == (
            "No licence data instance found for given run number 999\n"
            "hmrc_run_number 999 does not belong to Licence data mail\n"
        )

    def test_invalid_extract_type(self, capsys):
        self.mail.extract_type = ExtractTypeEnum.USAGE_DATA
        self.mail.save()

        call_command("resend_email", hmrc_run_number=self.ld.hmrc_run_number)

        captured = capsys.readouterr()
        assert captured.err == "Unexpected extract_type for the mail the_licence_data_file\n"

    def test_invalid_status(self, capsys):
        self.mail.status = MailStatusEnum.REPLY_RECEIVED
        self.mail.save()

        call_command("resend_email", hmrc_run_number=self.ld.hmrc_run_number)

        captured = capsys.readouterr()
        assert (
            captured.err
            == "Mail is expected to be in 'reply_pending' status but current status is reply_received\n"
        )

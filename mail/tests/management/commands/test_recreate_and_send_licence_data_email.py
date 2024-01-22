import datetime as dt
import json
from unittest import mock

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command
from freezegun import freeze_time

from mail.chief.email import EmailMessageData
from mail.chief.licence_reply import LicenceReplyProcessor
from mail.enums import ExtractTypeEnum, MailStatusEnum, SourceEnum
from mail.models import LicenceData, LicencePayload, Mail


class TestResendLicenceDataEmail:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        db,
        sanctions_insert_payload,
        fa_oil_insert_payload,
        fa_dfl_insert_payload,
        fa_sil_insert_payload,
    ):
        self.sanctions_ref = sanctions_insert_payload["reference"]
        self.fa_oil_ref = fa_oil_insert_payload["reference"]
        self.fa_dfl_ref = fa_dfl_insert_payload["reference"]
        self.fa_sil_ref = fa_sil_insert_payload["reference"]

        self.mail = Mail.objects.create(
            status=MailStatusEnum.REPLY_PARTIALLY_PROCESSED,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename="the_licence_data_file",
            edi_data="lovely data",
            sent_at=dt.datetime(2024, 1, 1),
        )

        self.ld = LicenceData.objects.create(
            hmrc_run_number=123, licence_ids="", source=SourceEnum.ICMS, mail=self.mail
        )
        for data in [
            fa_dfl_insert_payload,
            fa_oil_insert_payload,
            fa_sil_insert_payload,
            sanctions_insert_payload,
        ]:
            licence = LicencePayload.objects.create(
                action=data["action"],
                icms_id=data["id"],
                reference=data["reference"],
                data=data,
                is_processed=True,
            )
            self.ld.licence_payloads.add(licence)

        # Fake a partially valid licenceReply file (only the first two payloads are referenced)
        self.mail.response_data = (
            "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\123\n"
            f"2\\accepted\\{self.sanctions_ref}\n"
            f"3\\rejected\\{self.fa_oil_ref}\n"
            "4\\error\\1234\\Invalid thingy\n"
            "5\\error\\76543\\Invalid commodity “1234A6” in line 23\n"
            "6\\end\\rejected\\4\n"
            "7\\fileError\\9\\CHIEF server application error\n"
        )
        self.mail.save()

    def test_mail_is_partially_valid(self):
        processor = LicenceReplyProcessor.load_from_mail(self.mail)
        assert processor.reply_file_is_partially_valid()

    @freeze_time("2024-01-21T14:10:59+00:00")
    @mock.patch("mail.management.commands.recreate_and_send_licence_data_email.send_email_wrapper")
    def test_can_recreate_and_resend_licence_data_email(self, mock_send_email_wrapper):
        call_command(
            "recreate_and_send_licence_data_email", hmrc_run_number=self.ld.hmrc_run_number
        )

        # Check we sent the expected email:
        #   Run number is the next available
        #   Only the unprocessed references are sent to HMRC (fa_dfl_ref and fa_sil_ref)
        expected_mdo = EmailMessageData(
            receiver=settings.OUTGOING_EMAIL_USER,
            subject="CHIEF_LIVE_ILBDOTI_licenceData_124_202401211410",
            body=None,
            attachment=(
                "CHIEF_LIVE_ILBDOTI_licenceData_124_202401211410",
                "1\\fileHeader\\ILBDOTI\\CHIEF\\licenceData\\202401211410\\124\\N\n"
                f"2\\licence\\{self.fa_dfl_ref}\\insert\\GBSIL1111111C\\SIL\\I\\20220114\\20220714\n"
                "3\\trader\\\\GB665544332211000\\\\\\DFL Organisation\\line_1\\line_2\\line_3\\line_4\\\\S881ZZ\n"
                "4\\country\\US\\\\O\n"
                "5\\restrictions\\Sample restrictions\n"
                "6\\line\\1\\\\\\\\\\Sample goods description\\O\\\\\\\\\\\\\\\\\\\\\n"
                "7\\end\\licence\\6\n"
                f"8\\licence\\{self.fa_sil_ref}\\insert\\GBSIL3333333H\\SIL\\I\\20220629\\20241229\n"
                "9\\trader\\\\GB123456654321000\\\\\\SIL Organisation\\line_1\\line_2\\line_3\\\\\\S227ZZ\n"
                "10\\country\\US\\\\O\n"
                "11\\restrictions\\Sample restrictions\n"
                "12\\line\\1\\\\\\\\\\Sample goods description 1\\Q\\\\030\\\\1\\\\\\\\\\\\\n"
                "13\\line\\2\\\\\\\\\\Sample goods description 2\\Q\\\\030\\\\2\\\\\\\\\\\\\n"
                "14\\line\\3\\\\\\\\\\Sample goods description 3\\Q\\\\030\\\\3\\\\\\\\\\\\\n"
                "15\\line\\4\\\\\\\\\\Sample goods description 4\\Q\\\\030\\\\4\\\\\\\\\\\\\n"
                "16\\line\\5\\\\\\\\\\Sample goods description 5\\Q\\\\030\\\\5\\\\\\\\\\\\\n"
                "17\\line\\6\\\\\\\\\\Unlimited Description goods line\\O\\\\\\\\\\\\\\\\\\\\\n"
                "18\\end\\licence\\11\n"
                "19\\fileTrailer\\2\n",
            ),
        )

        mock_send_email_wrapper.assert_called_once_with(expected_mdo)

        # Check the mail has been archived
        self.mail.refresh_from_db()
        assert self.mail.status == MailStatusEnum.REPLY_PROCESSED

        # Check there is a new mail / LD record.
        ld = LicenceData.objects.get(hmrc_run_number=124)
        new_mail = ld.mail
        assert new_mail.status == MailStatusEnum.REPLY_PENDING
        assert json.loads(ld.licence_ids) == [self.fa_dfl_ref, self.fa_sil_ref]

    def test_invalid_status(self, capsys):
        self.ld.mail.status = MailStatusEnum.REPLY_RECEIVED
        self.ld.mail.save()

        with pytest.raises(
            CommandError, match="This command only works with partially processed mail."
        ):
            call_command(
                "recreate_and_send_licence_data_email", hmrc_run_number=self.ld.hmrc_run_number
            )

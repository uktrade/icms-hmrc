import uuid

from django.core.management import call_command
from django.test import override_settings
from freezegun import freeze_time

from mail.enums import (
    ExtractTypeEnum,
    FakeChiefLicenceReplyEnum,
    LicenceActionEnum,
    MailStatusEnum,
    SourceEnum,
)
from mail.models import LicenceData, LicencePayload, Mail


class TestDevProcessLicenceReply:
    def setup_test_data(self):
        self.mail: Mail = Mail.objects.create(
            status=MailStatusEnum.REPLY_PENDING,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename="the_licence_data_file",
            edi_data="lovely data",
        )
        ld: LicenceData = LicenceData.objects.create(
            licence_ids="", hmrc_run_number=29236, source=SourceEnum.ICMS, mail=self.mail
        )

        # fake some licence payload references for the test file
        for reference in ["ABC12345", "ABC12346", "ABC12348", "ABC12347"]:
            payload = LicencePayload.objects.create(
                icms_id=uuid.uuid4(),
                reference=reference,
                action=LicenceActionEnum.INSERT,
                is_processed=True,
            )
            ld.licence_payloads.add(payload)

    @staticmethod
    def call_command(*args, **kwargs):
        call_command("dev_fake_licence_reply", *args, **kwargs)

    @override_settings(APP_ENV="production")
    def test_dev_fake_licence_reply_disabled(self, db, capsys):
        self.call_command()

        captured = capsys.readouterr()
        assert (
            captured.out
            == "Desired outcome: accept\nThis command is only for development environments\n"
        )

    @override_settings(DEBUG=True)
    def test_dev_fake_licence_reply_nothing_to_process(self, db, capsys):
        self.call_command()

        captured = capsys.readouterr()
        assert (
            captured.out == "Desired outcome: accept\nNo mail records with reply_pending status\n"
        )

    @freeze_time("2022-11-10T14:10:00+00:00")
    @override_settings(DEBUG=True)
    def test_dev_fake_licence_reply_accepted(self, transactional_db, capsys):
        self.setup_test_data()

        # test
        self.call_command()

        # assertions
        self.mail.refresh_from_db()

        captured = capsys.readouterr()
        assert captured.out == (
            "Desired outcome: accept\n"
            f"Mail instance found: {self.mail.id} - the_licence_data_file\n"
            "Successfully faked LicenceReply file from CHIEF.\n"
        )

        assert self.mail.status == MailStatusEnum.REPLY_RECEIVED

        assert self.mail.response_filename == "CHIEF_licenceReply_29236_202211101410"
        assert self.mail.response_data == (
            "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202211101410\\29236\n"
            "2\\accepted\\ABC12345\n"
            "3\\accepted\\ABC12346\n"
            "4\\accepted\\ABC12348\n"
            "5\\accepted\\ABC12347\n"
            "6\\fileTrailer\\4\\0\\0"
        )

    @freeze_time("2022-11-10T14:10:00+00:00")
    @override_settings(DEBUG=True)
    def test_dev_fake_licence_reply_rejected(self, transactional_db, capsys):
        self.setup_test_data()

        # test
        self.call_command(FakeChiefLicenceReplyEnum.REJECT)

        # assertions
        self.mail.refresh_from_db()

        captured = capsys.readouterr()
        assert captured.out == (
            "Desired outcome: reject\n"
            f"Mail instance found: {self.mail.id} - the_licence_data_file\n"
            "Successfully faked LicenceReply file from CHIEF.\n"
        )

        assert self.mail.status == MailStatusEnum.REPLY_RECEIVED

        assert self.mail.response_filename == "CHIEF_licenceReply_29236_202211101410"

        assert self.mail.response_data == (
            "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202211101410\\29236\n"
            "2\\rejected\\ABC12345\n"
            "3\\error\\12345\\Fake error message for ABC12345\n"
            "4\\end\\rejected\\3\n"
            "5\\rejected\\ABC12346\n"
            "6\\error\\12345\\Fake error message for ABC12346\n"
            "7\\end\\rejected\\3\n"
            "8\\rejected\\ABC12348\n"
            "9\\error\\12345\\Fake error message for ABC12348\n"
            "10\\end\\rejected\\3\n"
            "11\\rejected\\ABC12347\n"
            "12\\error\\12345\\Fake error message for ABC12347\n"
            "13\\end\\rejected\\3\n"
            "14\\fileTrailer\\0\\4\\0"
        )

    @freeze_time("2022-11-10T14:10:00+00:00")
    @override_settings(DEBUG=True)
    def test_dev_fake_licence_reply_file_error(self, transactional_db, capsys):
        self.setup_test_data()

        # test
        self.call_command(FakeChiefLicenceReplyEnum.FILE_ERROR)

        # assertions
        self.mail.refresh_from_db()

        captured = capsys.readouterr()
        assert captured.out == (
            "Desired outcome: file_error\n"
            f"Mail instance found: {self.mail.id} - the_licence_data_file\n"
            "Successfully faked LicenceReply file from CHIEF.\n"
        )

        assert self.mail.status == MailStatusEnum.REPLY_RECEIVED

        assert self.mail.response_filename == "CHIEF_licenceReply_29236_202211101410"

        assert self.mail.response_data == (
            "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202211101410\\29236\n"
            "2\\fileError\\18\\Record type 'fileHeader' not recognised\\99\n"
            "3\\fileTrailer\\0\\0\\1"
        )

    @override_settings(DEBUG=True)
    def test_dev_fake_licence_reply_unknown_error(self, transactional_db, capsys):
        self.setup_test_data()

        # test
        self.call_command(FakeChiefLicenceReplyEnum.UNKNOWN_ERROR)

        # assertions
        self.mail.refresh_from_db()

        captured = capsys.readouterr()
        assert captured.out == (
            "Desired outcome: unknown_error\n"
            f"Mail instance found: {self.mail.id} - the_licence_data_file\n"
            "Returning without updating mail record to simulate no response from HMRC.\n"
        )

        assert self.mail.status == MailStatusEnum.REPLY_PENDING

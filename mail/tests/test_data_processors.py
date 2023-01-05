from django.db import IntegrityError

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.builders import build_sent_file_data, build_sent_filename
from mail.models import LicenceData, Mail, UsageData
from mail.tests.libraries.client import LiteHMRCTestClient


class TestDataProcessors(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

        self.hmrc_run_number = 28
        self.source_run_number = 15
        self.mail = Mail.objects.create(
            edi_data=self.licence_data_file_body.decode("utf-8"),
            extract_type=ExtractTypeEnum.USAGE_DATA,
            status=ReceptionStatusEnum.REPLY_SENT,
            edi_filename=self.licence_data_reply_name,
        )

        self.licence_data = LicenceData.objects.create(
            mail=self.mail,
            hmrc_run_number=self.hmrc_run_number,
            source_run_number=self.source_run_number,
            source=SourceEnum.SPIRE,
        )

        self.usage_data = UsageData.objects.create(
            mail=self.mail,
            spire_run_number=self.source_run_number,
            hmrc_run_number=self.hmrc_run_number,
        )

    def test_mail_create_fails_with_empty_edi_values(self):
        with self.assertRaises(IntegrityError):
            Mail.objects.create()

    def test_build_sent_filename(self):
        run_number = 4321
        filename = "abc_xyz_nnn_yyy_<runnumber>_datetime"

        self.assertEqual(build_sent_filename(filename, run_number), f"abc_xyz_nnn_yyy_{run_number}_datetime")

    def test_build_sent_file_data(self):
        run_number = 4321
        file_data = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\{:04d}{:02d}{:02d}{:02d}{:02d}\\1234"
            + "\n2\\licence\\1234\\insert\\GBSIEL/2020/0000001/P\\siel\\E\\1234\\1234"
            + "\n3\\trader\\0192301\\123791\\20200602\\20220602\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Tennessee\\99580"
        )
        expected_file_data = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\{:04d}{:02d}{:02d}{:02d}{:02d}\\4321"
            + "\n2\\licence\\1234\\insert\\GBSIEL/2020/0000001/P\\siel\\E\\1234\\1234"
            + "\n3\\trader\\0192301\\123791\\20200602\\20220602\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Tennessee\\99580"
        )
        self.assertEqual(build_sent_file_data(file_data, run_number), expected_file_data)

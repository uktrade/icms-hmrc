import datetime
import uuid
from pathlib import Path

from django.conf import settings
from django.test import override_settings, testcases

from mail.enums import ChiefSystemEnum, LicenceActionEnum, LicenceTypeEnum
from mail.libraries import builders
from mail.libraries.email_message_dto import EmailMessageDto
from mail.models import LicencePayload


class BuildEmailMessageTest(testcases.TestCase):
    maxDiff = None

    def test_build_email_message(self):
        attachment = "30 \U0001d5c4\U0001d5c6/\U0001d5c1 \u5317\u4EB0"
        email_message_dto = EmailMessageDto(
            run_number=1,
            sender="This...gets....ignored ¯\\_(ツ)_//¯",
            receiver="receiver@email_domain.com",
            date="Mon, 17 May 2021 14:20:18 +0100",
            body=None,
            subject="Some subject",
            attachment=["some filename", attachment],
            raw_data="",
        )

        mime_multipart = builders.build_email_message(email_message_dto)
        mime_multipart.set_boundary("===============8537751789001939036==")

        self.assertEqual(
            mime_multipart.as_string(),
            (
                'Content-Type: multipart/mixed; boundary="===============8537751789001939036=="\n'
                "MIME-Version: 1.0\n"
                f"From: {settings.EMAIL_USER}\n"
                f"To: receiver@email_domain.com\n"
                "Subject: Some subject\n"
                "name: Some subject\n\n"
                "--===============8537751789001939036==\n"
                'Content-Type: text/plain; charset="iso-8859-1"\n'
                "MIME-Version: 1.0\n"
                "Content-Transfer-Encoding: quoted-printable\n\n"
                "\n\n\n"
                "--===============8537751789001939036==\n"
                "Content-Type: application/octet-stream\n"
                "MIME-Version: 1.0\n"
                "Content-Transfer-Encoding: base64\n"
                'Content-Disposition: attachment; filename="some filename"\n'
                "Content-Transfer-Encoding: 7bit\n"
                "name: Some subject\n\n"
                "30 km/h Bei Jing \n"
                "--===============8537751789001939036==--\n"
            ),
        )


class BuildLicenceDataFileTests(testcases.TestCase):
    def test_filename_datetime(self):
        # Use single digits in some values to check the output is zero-padded.
        data = [
            (datetime.datetime(1999, 12, 31), "CHIEF_LIVE_ILBDOTI_licenceData_1_199912310000"),
            (datetime.datetime(2022, 1, 1), "CHIEF_LIVE_ILBDOTI_licenceData_1_202201010000"),
            (datetime.datetime(2022, 1, 1, 9, 8, 7), "CHIEF_LIVE_ILBDOTI_licenceData_1_202201010908"),
        ]

        for when, expected in data:
            with self.subTest(when=when, expected=expected):
                filename, _ = builders.build_licence_data_file(LicencePayload.objects.none(), 1, when)

                self.assertEqual(filename, expected)

    def test_filename_system_identifier(self):
        # Originally the only system was SPIRE. But you can change that.
        when = datetime.datetime(1999, 12, 31)

        with self.settings(CHIEF_SOURCE_SYSTEM="FOO"):
            filename, _ = builders.build_licence_data_file(LicencePayload.objects.none(), 1, when)

        self.assertEqual(filename, "CHIEF_LIVE_FOO_licenceData_1_199912310000")


@override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS)
class TestBuildICMSLicenceDataFAOIL(testcases.TestCase):
    def setUp(self) -> None:
        self.licence = LicencePayload.objects.create(
            lite_id="deaa301d-d978-473b-b76b-da275f28f447",
            reference="IMA/2022/00001",
            action=LicenceActionEnum.INSERT,
            data={
                "type": LicenceTypeEnum.IMPORT_OIL.value,
                "reference": "IMA/2022/00001",
                "licence_reference": "GBOIL2222222C",
                "start_date": "2022-06-06",
                "end_date": "2025-05-30",
                "organisation": {
                    "eori_number": "GB112233445566000",
                    "name": "org name",
                    "address": {
                        "line_1": "line_1",
                        "line_2": "line_2",
                        "line_3": "line_3",
                        "line_4": "line_4",
                        "line_5": "line_5",
                        "postcode": "S118ZZ",
                    },
                },
                "country_group": "G001",
                "restrictions": "Some restrictions.\n\n Some more restrictions",
                "goods": [
                    {
                        "description": (
                            "Firearms, component parts thereof, or ammunition of"
                            " any applicable commodity code, other than those"
                            " falling under Section 5 of the Firearms Act 1968"
                            " as amended."
                        )
                    }
                ],
            },
        )

    def test_generate_licence_data_file(self):
        self.assertEqual(self.licence.reference, "IMA/2022/00001")

        licences = LicencePayload.objects.filter(pk=self.licence.pk)
        run_number = 1
        when = datetime.datetime(2022, 1, 1, 10, 11, 00)

        filename, file_content = builders.build_licence_data_file(licences, run_number, when)

        self.assertEqual(filename, f"CHIEF_LIVE_ILBDOTI_licenceData_1_202201011011")

        test_file = Path("mail/tests/files/icms/licence_data_files/fa_oil_insert")
        expected_content = test_file.read_text()
        self.assertEqual(expected_content, file_content)

    def test_generate_licence_data_file_replace(self):
        # Get the original licence data
        replace_data = self.licence.data
        replace_data["reference"] = "IMA/2022/00001/1"
        replace_data["organisation"]["name"] = "org new name"

        replace_licence = LicencePayload.objects.create(
            lite_id=uuid.uuid4(), reference="IMA/2022/00001/1", action=LicenceActionEnum.REPLACE, data=replace_data
        )

        licences = LicencePayload.objects.filter(pk=replace_licence.pk)
        run_number = 2
        when = datetime.datetime(2022, 1, 2, 10, 11, 00)

        filename, file_content = builders.build_licence_data_file(licences, run_number, when)

        self.assertEqual(filename, f"CHIEF_LIVE_ILBDOTI_licenceData_2_202201021011")
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_oil_replace")
        expected_content = test_file.read_text()
        self.assertEqual(expected_content, file_content)


@override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS)
class TestBuildICMSLicenceDataFADFL(testcases.TestCase):
    def setUp(self) -> None:
        org_data = {
            "eori_number": "GB665544332211000",
            "name": "DFL Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "line_4",
                "line_5": "",
                "postcode": "S881ZZ",
            },
        }

        restrictions = "Sample restrictions"

        LicencePayload.objects.create(
            lite_id="4277dd90-7ac0-4f48-b228-94c4a2fc61b2",
            reference="IMA/2022/00002",
            action=LicenceActionEnum.INSERT,
            data={
                "type": LicenceTypeEnum.IMPORT_DFL.value,
                "reference": "IMA/2022/00002",
                "licence_reference": "GBSIL1111111C",
                "start_date": "2022-01-14",
                "end_date": "2022-07-14",
                "organisation": org_data,
                "country_code": "US",
                "restrictions": restrictions,
                "goods": [{"description": "Sample goods description"}],
            },
        )

        LicencePayload.objects.create(
            lite_id="f4142c5a-19f8-40b4-a9a8-46362eaa85c6",
            reference="IMA/2022/00003",
            action=LicenceActionEnum.INSERT,
            data={
                "type": LicenceTypeEnum.IMPORT_DFL.value,
                "reference": "IMA/2022/00003",
                "licence_reference": "GBSIL9089278D",
                "start_date": "2022-01-14",
                "end_date": "2022-07-14",
                "organisation": org_data,
                "country_code": "US",
                "restrictions": restrictions,
                "goods": [{"description": "Sample goods description 2"}],
            },
        )

        self.test_file = Path("mail/tests/files/icms/licence_data_files/fa_dfl_insert")
        self.assertTrue(self.test_file.is_file())

    def test_generate_licence_data_file(self):
        # There should be two licences
        licences = LicencePayload.objects.all()
        self.assertEqual(licences.count(), 2)

        run_number = 1
        when = datetime.datetime(2022, 1, 1, 10, 11, 00)

        filename, file_content = builders.build_licence_data_file(licences, run_number, when)

        self.assertEqual(filename, f"CHIEF_LIVE_ILBDOTI_licenceData_1_202201011011")

        expected_content = self.test_file.read_text()
        self.assertEqual(expected_content, file_content)


@override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS)
class TestBuildICMSLicenceDataFASIL(testcases.TestCase):
    def setUp(self) -> None:
        org_data = {
            "eori_number": "GB123456654321000",
            "name": "SIL Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "",
                "line_5": "",
                "postcode": "S227ZZ",
            },
        }

        restrictions = "Sample restrictions"

        goods = [
            {"description": "Sample goods description 1", "quantity": 1, "controlled_by": "Q", "unit": 30},
            {"description": "Sample goods description 2", "quantity": 2, "controlled_by": "Q", "unit": 30},
            {"description": "Sample goods description 3", "quantity": 3, "controlled_by": "Q", "unit": 30},
            {"description": "Sample goods description 4", "quantity": 4, "controlled_by": "Q", "unit": 30},
            {"description": "Sample goods description 5", "quantity": 5, "controlled_by": "Q", "unit": 30},
            {"description": "Unlimited Description goods line", "controlled_by": "O"},
        ]

        LicencePayload.objects.create(
            lite_id="4277dd90-7ac0-4f48-b228-94c4a2fc61b2",
            reference="IMA/2022/00003",
            action=LicenceActionEnum.INSERT,
            data={
                "type": LicenceTypeEnum.IMPORT_SIL.value,
                "reference": "IMA/2022/00003",
                "licence_reference": "GBSIL3333333H",
                "start_date": "2022-06-29",
                "end_date": "2024-12-29",
                "organisation": org_data,
                "country_code": "US",
                "restrictions": restrictions,
                "goods": goods,
            },
        )

        self.test_file = Path("mail/tests/files/icms/licence_data_files/fa_sil_insert")
        self.assertTrue(self.test_file.is_file())

    def test_generate_licence_data_file(self):
        licences = LicencePayload.objects.all()
        self.assertEqual(licences.count(), 1)

        run_number = 1
        when = datetime.datetime(2022, 1, 1, 10, 11, 00)

        filename, file_content = builders.build_licence_data_file(licences, run_number, when)

        self.assertEqual(filename, f"CHIEF_LIVE_ILBDOTI_licenceData_1_202201011011")

        self.maxDiff = None
        expected_content = self.test_file.read_text()
        self.assertEqual(expected_content, file_content)


@override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS)
class TestBuildICMSLicenceDataSanction(testcases.TestCase):
    def setUp(self) -> None:
        org_data = {
            "eori_number": "GB112233445566000",
            "name": "Sanction Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "",
                "line_5": "",
                "postcode": "S227ZZ",
            },
        }

        restrictions = ""
        goods = [
            {"commodity": "7214993100", "quantity": 26710, "controlled_by": "Q", "unit": 23},
            {"commodity": "7214997100", "quantity": 48042, "controlled_by": "Q", "unit": 23},
            {"commodity": "7215508000", "quantity": 4952, "controlled_by": "Q", "unit": 23},
        ]

        LicencePayload.objects.create(
            lite_id="4277dd90-7ac0-4f48-b228-94c4a2fc61b2",
            reference="IMA/2022/00004",
            action=LicenceActionEnum.INSERT,
            data={
                "type": LicenceTypeEnum.IMPORT_SAN.value,
                "reference": "IMA/2022/00004",
                "licence_reference": "GBSAN4444444A",
                "start_date": "2022-06-29",
                "end_date": "2024-12-29",
                "organisation": org_data,
                "country_code": "RU",
                "restrictions": restrictions,
                "goods": goods,
            },
        )

        self.test_file = Path("mail/tests/files/icms/licence_data_files/sanction_insert")
        self.assertTrue(self.test_file.is_file())

    def test_generate_licence_data_file(self):
        licences = LicencePayload.objects.all()
        self.assertEqual(licences.count(), 1)

        run_number = 1
        when = datetime.datetime(2022, 1, 1, 10, 11, 00)

        filename, file_content = builders.build_licence_data_file(licences, run_number, when)

        self.assertEqual(filename, f"CHIEF_LIVE_ILBDOTI_licenceData_1_202201011011")

        self.maxDiff = None
        expected_content = self.test_file.read_text()
        self.assertEqual(expected_content, file_content)

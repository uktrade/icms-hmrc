import datetime
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
            sender=settings.HMRC_ADDRESS,
            receiver=settings.SPIRE_ADDRESS,
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
                f"To: {settings.SPIRE_ADDRESS}\n"
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
            (datetime.datetime(1999, 12, 31), "CHIEF_LIVE_SPIRE_licenceData_1_199912310000"),
            (datetime.datetime(2022, 1, 1), "CHIEF_LIVE_SPIRE_licenceData_1_202201010000"),
            (datetime.datetime(2022, 1, 1, 9, 8, 7), "CHIEF_LIVE_SPIRE_licenceData_1_202201010908"),
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
class TestBuildICMSLicenceData(testcases.TestCase):
    def setUp(self) -> None:
        self.licence = LicencePayload.objects.create(
            lite_id="deaa301d-d978-473b-b76b-da275f28f447",
            reference="GBOIL9089667C",
            action=LicenceActionEnum.INSERT,
            data={
                "type": LicenceTypeEnum.IMPORT_OIL.value,
                "case_reference": "IMA/2022/00001",
                "start_date": "2022-06-06",
                "end_date": "2025-05-30",
                "organisation": {
                    "eori_number": "112233445566",
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

        self.test_file = Path("mail/tests/files/icms/icms_chief_licence_data_file")
        self.assertTrue(self.test_file.is_file())

    def test_generate_icms_licence_file(self):
        self.assertEqual(self.licence.reference, "GBOIL9089667C")

        licences = LicencePayload.objects.filter(pk=self.licence.pk)
        run_number = 1
        when = datetime.datetime(2022, 1, 1, 10, 11, 00)

        filename, file_content = builders.build_licence_data_file(licences, run_number, when)

        self.assertEqual(filename, f"CHIEF_LIVE_ILBDOTI_licenceData_1_202201011011")

        expected_content = self.test_file.read_text()
        self.assertEqual(expected_content, file_content)

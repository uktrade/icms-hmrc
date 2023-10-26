from pathlib import Path

import requests
from django.conf import settings
from django.test import override_settings, testcases
from django.urls import reverse

from mail import tasks
from mail.enums import ChiefSystemEnum, ReceptionStatusEnum
from mail.models import LicenceData, LicencePayload, Mail
from mail.tests.test_serializers import (
    get_valid_fa_sil_payload,
    get_valid_fa_sil_revoke_payload,
    get_valid_sanctions_payload,
)


def clear_stmp_mailbox():
    response = requests.get(f"{settings.MAILHOG_URL}/api/v2/messages")
    for message in response.json()["items"]:
        idx = message["ID"]
        requests.delete(f"{settings.MAILHOG_URL}/api/v1/messages/{idx}")


def get_smtp_body():
    response = requests.get(f"{settings.MAILHOG_URL}/api/v2/messages")
    return response.json()["items"][0]["MIME"]["Parts"][1]["Body"]


@override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS, USE_LEGACY_EMAIL_CODE=True)
class ICMSEndToEndTests(testcases.TestCase):
    def test_icms_send_email_to_hmrc_fa_oil_e2e(self):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=ReceptionStatusEnum.REPLY_SENT)

        data = {
            "type": "OIL",
            "action": "insert",
            "id": "deaa301d-d978-473b-b76b-da275f28f447",
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
                    "postcode": "S118ZZ",  # /PS-IGNORE
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
                    ),
                }
            ],
        }

        resp = self.client.post(
            reverse("mail:update_licence"), data={"licence": data}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        tasks.send_licence_data_to_hmrc.apply()

        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_oil_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        self._assert_reply_pending("IMA/2022/00001")

        # Check licence_payload records have been created
        ld = LicenceData.objects.get(hmrc_run_number=1)

        assert ld.licence_payloads.count() == 1
        licence_payload: LicencePayload = ld.licence_payloads.first()
        assert licence_payload.reference == "IMA/2022/00001"

    def test_icms_send_email_to_hmrc_fa_dfl_e2e(self):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=ReceptionStatusEnum.REPLY_SENT)

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

        data = {
            "type": "DFL",
            "action": "insert",
            "id": "4277dd90-7ac0-4f48-b228-94c4a2fc61b2",
            "reference": "IMA/2022/00002",
            "licence_reference": "GBSIL1111111C",
            "start_date": "2022-01-14",
            "end_date": "2022-07-14",
            "organisation": org_data,
            "country_code": "US",
            "restrictions": restrictions,
            "goods": [{"description": "Sample goods description"}],
        }
        resp = self.client.post(
            reverse("mail:update_licence"), data={"licence": data}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        data = {
            "type": "DFL",
            "action": "insert",
            "id": "f4142c5a-19f8-40b4-a9a8-46362eaa85c6",
            "reference": "IMA/2022/00003",
            "licence_reference": "GBSIL9089278D",
            "start_date": "2022-01-14",
            "end_date": "2022-07-14",
            "organisation": org_data,
            "country_code": "US",
            "restrictions": restrictions,
            "goods": [{"description": "Sample goods description 2"}],
        }
        resp = self.client.post(
            reverse("mail:update_licence"), data={"licence": data}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_dfl_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        for ref in ["IMA/2022/00002", "IMA/2022/00003"]:
            self._assert_reply_pending(ref)

    def test_icms_send_email_to_hmrc_fa_sil_e2e(self):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=ReceptionStatusEnum.REPLY_SENT)

        data = get_valid_fa_sil_payload()
        resp = self.client.post(
            reverse("mail:update_licence"), data={"licence": data}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_sil_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        self._assert_reply_pending("IMA/2022/00003")

    def test_icms_send_email_to_hmrc_sanctions_e2e(self):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=ReceptionStatusEnum.REPLY_SENT)

        data = get_valid_sanctions_payload()
        resp = self.client.post(
            reverse("mail:update_licence"), data={"licence": data}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/sanction_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        self._assert_reply_pending("IMA/2022/00004")

    def test_icms_send_email_to_hmrc_fa_sil_cancel_e2e(self):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=ReceptionStatusEnum.REPLY_SENT)

        data = get_valid_fa_sil_revoke_payload()
        resp = self.client.post(
            reverse("mail:update_licence"), data={"licence": data}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_sil_cancel")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        self._assert_reply_pending("IMA/2023/00001")

    def _assert_reply_pending(self, case_reference):
        matching_licences = LicenceData.objects.filter(licence_ids__contains=case_reference)
        matching_licences_count = matching_licences.count()

        if matching_licences_count > 1:
            raise AssertionError("Too many matches for licence '%s'", case_reference)

        elif matching_licences_count == 0:
            raise AssertionError("No matches for licence '%s'", case_reference)

        mail = matching_licences.first().mail
        self.assertEqual(mail.status, "reply_pending", f"{case_reference} has incorrect status")

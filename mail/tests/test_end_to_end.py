from pathlib import Path
from urllib.parse import quote

import requests
from django.conf import settings
from django.test import override_settings, testcases
from django.urls import reverse

from mail.enums import ChiefSystemEnum
from mail.tests.libraries.client import LiteHMRCTestClient
from mail.tests.test_serializers import get_valid_fa_sil_payload, get_valid_sanctions_payload


def clear_stmp_mailbox():
    response = requests.get(f"{settings.MAILHOG_URL}/api/v2/messages")
    for message in response.json()["items"]:
        idx = message["ID"]
        requests.delete(f"{settings.MAILHOG_URL}/api/v1/messages/{idx}")


def get_smtp_body():
    response = requests.get(f"{settings.MAILHOG_URL}/api/v2/messages")
    return response.json()["items"][0]["MIME"]["Parts"][1]["Body"]


class EndToEndTests(LiteHMRCTestClient):
    def test_send_email_to_hmrc_e2e(self):
        clear_stmp_mailbox()
        self.client.get(reverse("mail:set_all_to_reply_sent"))
        self.client.post(
            reverse("mail:update_licence"), data=self.licence_payload_json, content_type="application/json"
        )
        self.client.get(reverse("mail:send_updates_to_hmrc"))
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]
        run_number = body.split("\n")[0].split("\\")[6]
        expected_mail_body = rf"""1\fileHeader\SPIRE\CHIEF\licenceData\{ymdhm_timestamp}\{run_number}\N
2\licence\20200000001P\insert\GBSIEL/2020/0000001/P\SIE\E\20200602\20220602
3\trader\\GB123456789000\20200602\20220602\Organisation\might\248 James Key Apt. 515\Apt. 942\West Ashleyton\Farnborough\GU40 2LX
4\country\GB\\D
5\foreignTrader\End User\42 Road, London, Buckinghamshire\\\\\\GB
6\restrictions\Provisos may apply please see licence
7\line\1\\\\\Sporting shotgun\Q\\030\\10\\\\\\
8\end\licence\7
9\fileTrailer\1"""
        assert body == expected_mail_body  # nosec
        encoded_reference_code = quote("GBSIEL/2020/0000001/P", safe="")
        response = self.client.get(f"{reverse('mail:licence')}?id={encoded_reference_code}")
        assert response.json()["status"] == "reply_pending"  # nosec


@override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS)
class ICMSEndToEndTests(testcases.TestCase):
    def test_icms_send_email_to_hmrc_fa_oil_e2e(self):
        clear_stmp_mailbox()
        self.client.get(reverse("mail:set_all_to_reply_sent"))

        data = {
            "type": "OIL",
            "action": "insert",
            "id": "deaa301d-d978-473b-b76b-da275f28f447",
            "reference": "GBOIL2222222C",
            "case_reference": "IMA/2022/00001",
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

        resp = self.client.post(reverse("mail:update_licence"), data={"licence": data}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

        self.client.get(reverse("mail:send_updates_to_hmrc"))
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/icms_chief_licence_data_file_fa_oil")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        encoded_reference_code = quote("GBOIL2222222C", safe="")
        response = self.client.get(f"{reverse('mail:licence')}?id={encoded_reference_code}")
        self.assertEqual(response.json()["status"], "reply_pending")

    def test_icms_send_email_to_hmrc_fa_dfl_e2e(self):
        clear_stmp_mailbox()
        self.client.get(reverse("mail:set_all_to_reply_sent"))

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
            "reference": "GBSIL1111111C",
            "case_reference": "IMA/2022/00002",
            "start_date": "2022-01-14",
            "end_date": "2022-07-14",
            "organisation": org_data,
            "country_code": "US",
            "restrictions": restrictions,
            "goods": [{"description": "Sample goods description"}],
        }
        resp = self.client.post(reverse("mail:update_licence"), data={"licence": data}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

        data = {
            "type": "DFL",
            "action": "insert",
            "id": "f4142c5a-19f8-40b4-a9a8-46362eaa85c6",
            "reference": "GBSIL9089278D",
            "case_reference": "IMA/2022/00003",
            "start_date": "2022-01-14",
            "end_date": "2022-07-14",
            "organisation": org_data,
            "country_code": "US",
            "restrictions": restrictions,
            "goods": [{"description": "Sample goods description 2"}],
        }
        resp = self.client.post(reverse("mail:update_licence"), data={"licence": data}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

        self.client.get(reverse("mail:send_updates_to_hmrc"))
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/icms_chief_licence_data_file_fa_dfl")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        for ref in ["GBSIL1111111C", "GBSIL9089278D"]:
            encoded_reference_code = quote(ref, safe="")
            response = self.client.get(f"{reverse('mail:licence')}?id={encoded_reference_code}")
            self.assertEqual(response.json()["status"], "reply_pending", f"{ref} has incorrect status")

    def test_icms_send_email_to_hmrc_fa_sil_e2e(self):
        clear_stmp_mailbox()
        self.client.get(reverse("mail:set_all_to_reply_sent"))

        data = get_valid_fa_sil_payload()
        resp = self.client.post(reverse("mail:update_licence"), data={"licence": data}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

        self.client.get(reverse("mail:send_updates_to_hmrc"))
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/icms_chief_licence_data_file_fa_sil")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        encoded_reference_code = quote("GBSIL3333333H", safe="")
        response = self.client.get(f"{reverse('mail:licence')}?id={encoded_reference_code}")
        self.assertEqual(response.json()["status"], "reply_pending")

    def test_icms_send_email_to_hmrc_sanctions_e2e(self):
        clear_stmp_mailbox()
        self.client.get(reverse("mail:set_all_to_reply_sent"))

        data = get_valid_sanctions_payload()
        resp = self.client.post(reverse("mail:update_licence"), data={"licence": data}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

        self.client.get(reverse("mail:send_updates_to_hmrc"))
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/icms_chief_licence_data_file_sanction")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        self.assertEqual(expected_content, body)

        encoded_reference_code = quote("GBSAN4444444A", safe="")
        response = self.client.get(f"{reverse('mail:licence')}?id={encoded_reference_code}")
        self.assertEqual(response.json()["status"], "reply_pending")

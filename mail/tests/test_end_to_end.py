from pathlib import Path

import pytest
import requests
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from mail import tasks
from mail.enums import ChiefSystemEnum, MailStatusEnum
from mail.models import LicenceData, LicencePayload, Mail


def clear_stmp_mailbox():
    response = requests.get(f"{settings.MAILHOG_URL}/api/v2/messages")
    for message in response.json()["items"]:
        idx = message["ID"]
        requests.delete(f"{settings.MAILHOG_URL}/api/v1/messages/{idx}")


def get_smtp_body():
    response = requests.get(f"{settings.MAILHOG_URL}/api/v2/messages")
    return response.json()["items"][0]["MIME"]["Parts"][1]["Body"]


class TestICMSEndToEnd:
    @pytest.fixture(autouse=True)
    def _setup(self, db, client):
        self.client = client

        with override_settings(
            CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS,
            USE_LEGACY_EMAIL_CODE=True,
            HAWK_AUTHENTICATION_ENABLED=False,
        ):
            yield

    def test_icms_send_email_to_hmrc_fa_oil_e2e(self, fa_oil_insert_payload):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=MailStatusEnum.REPLY_PROCESSED)

        resp = self.client.post(
            reverse("mail:update_licence"),
            data={"licence": fa_oil_insert_payload},
            content_type="application/json",
        )
        assert resp.status_code == 201

        tasks.send_licence_data_to_hmrc.apply()

        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_oil_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        assert expected_content == body

        self._assert_reply_pending("IMA/2022/00001")

        # Check licence_payload records have been created
        ld = LicenceData.objects.get(hmrc_run_number=1)

        assert ld.licence_payloads.count() == 1
        licence_payload: LicencePayload = ld.licence_payloads.first()
        assert licence_payload.reference == "IMA/2022/00001"

    def test_icms_send_email_to_hmrc_fa_dfl_e2e(
        self, fa_dfl_insert_payload, fa_dfl_insert_payload_2
    ):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=MailStatusEnum.REPLY_PROCESSED)

        resp = self.client.post(
            reverse("mail:update_licence"),
            data={"licence": fa_dfl_insert_payload},
            content_type="application/json",
        )
        assert resp.status_code == 201

        resp = self.client.post(
            reverse("mail:update_licence"),
            data={"licence": fa_dfl_insert_payload_2},
            content_type="application/json",
        )
        assert resp.status_code == 201

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_dfl_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        assert expected_content == body

        for ref in ["IMA/2022/00002", "IMA/2022/00003"]:
            self._assert_reply_pending(ref)

    def test_icms_send_email_to_hmrc_fa_sil_e2e(self, fa_sil_insert_payload):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=MailStatusEnum.REPLY_PROCESSED)

        resp = self.client.post(
            reverse("mail:update_licence"),
            data={"licence": fa_sil_insert_payload},
            content_type="application/json",
        )
        assert resp.status_code == 201

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_sil_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        assert expected_content == body

        self._assert_reply_pending("IMA/2022/00003")

    def test_icms_send_email_to_hmrc_sanctions_e2e(self, sanctions_insert_payload):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=MailStatusEnum.REPLY_PROCESSED)

        resp = self.client.post(
            reverse("mail:update_licence"),
            data={"licence": sanctions_insert_payload},
            content_type="application/json",
        )
        assert resp.status_code == 201

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/sanction_insert")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        assert expected_content == body

        self._assert_reply_pending("IMA/2022/00004")

    def test_icms_send_email_to_hmrc_fa_sil_cancel_e2e(self, fa_sil_revoke_payload):
        clear_stmp_mailbox()
        Mail.objects.all().update(status=MailStatusEnum.REPLY_PROCESSED)

        resp = self.client.post(
            reverse("mail:update_licence"),
            data={"licence": fa_sil_revoke_payload},
            content_type="application/json",
        )
        assert resp.status_code == 201

        tasks.send_licence_data_to_hmrc.apply()
        body = get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]

        # Replace the hardcoded date in the test file with the one in the email.
        test_file = Path("mail/tests/files/icms/licence_data_files/fa_sil_cancel")
        expected_content = test_file.read_text().replace("202201011011", ymdhm_timestamp).strip()
        assert expected_content == body

        self._assert_reply_pending("IMA/2023/00001")

    def _assert_reply_pending(self, case_reference):
        matching_licences = LicenceData.objects.filter(licence_ids__contains=case_reference)
        matching_licences_count = matching_licences.count()

        if matching_licences_count > 1:
            raise AssertionError("Too many matches for licence '%s'", case_reference)

        elif matching_licences_count == 0:
            raise AssertionError("No matches for licence '%s'", case_reference)

        mail = matching_licences.first().mail
        assert mail.status, "reply_pending" == f"{case_reference} has incorrect status"

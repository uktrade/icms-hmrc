from django.test import tag
from django.urls import reverse
from rest_framework import status

from mail.enums import LicenceActionEnum
from mail.models import LicencePayload, LicenceIdMapping
from mail.tests.libraries.client import LiteHMRCTestClient


class UpdateLicenceEndpointTests(LiteHMRCTestClient):
    url = reverse("mail:update_licence")

    @tag("2448", "fail")
    def test_post_data_failure_no_data(self):
        data = {}

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @tag("2448", "success")
    def test_post_data_success(self):
        LicencePayload.objects.get().delete()
        initial_licence_count = LicencePayload.objects.count()
        response = self.client.post(self.url, data=self.licence_payload_json, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LicencePayload.objects.count(), initial_licence_count + 1)

    @tag("2448", "success")
    def test_post_data_idempotent(self):
        initial_licence_count = LicencePayload.objects.count()
        lp = LicencePayload.objects.get()
        lp.action = LicenceActionEnum.CANCEL
        lp.save()
        self.client.post(self.url, data=self.licence_payload_json, content_type="application/json")
        response = self.client.post(self.url, data=self.licence_payload_json, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LicencePayload.objects.count(), initial_licence_count + 1)

    @tag("1917", "update")
    def test_post_update_success(self):
        initial_licence_count = LicencePayload.objects.count()
        initial_licence_id_mapping_count = LicenceIdMapping.objects.count()

        lite_id = "09e21356-9e9d-418d-bd4d-9792333e8cc8"

        mapping = LicenceIdMapping.objects.get()

        data = self.licence_payload_json
        data["licence"]["id"] = "09e21356-9e9d-418d-bd4d-000000077777"
        data["licence"]["reference"] = "GBSIEL/2020/0000001/P/A"
        data["licence"]["old_id"] = lite_id
        data["licence"]["action"] = LicenceActionEnum.UPDATE
        response = self.client.post(self.url, data=self.licence_payload_json, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LicencePayload.objects.count(), initial_licence_count + 1)
        self.assertEqual(LicenceIdMapping.objects.count(), initial_licence_id_mapping_count + 1)

        self.assertTrue(
            LicencePayload.objects.filter(old_reference=mapping.reference, old_lite_id=mapping.lite_id).exists()
        )

    @tag("1917", "update-fail")
    def test_post_update_fail(self):
        initial_licence_count = LicencePayload.objects.count()
        initial_licence_id_mapping_count = LicenceIdMapping.objects.count()

        data = self.licence_payload_json
        data["licence"]["id"] = "09e21356-9e9d-418d-bd4d-000000077777"
        data["licence"]["reference"] = "GBSIEL/2020/0000001/P/A"
        data["licence"]["action"] = LicenceActionEnum.UPDATE
        response = self.client.post(self.url, data=self.licence_payload_json, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(LicencePayload.objects.count(), initial_licence_count)
        self.assertEqual(LicenceIdMapping.objects.count(), initial_licence_id_mapping_count)

    @tag("1917", "success")
    def test_post_data_ignore_old_id_field_success(self):
        LicencePayload.objects.get().delete()
        initial_licence_count = LicencePayload.objects.count()
        data = self.licence_payload_json
        data["licence"]["old_id"] = "09e21356-9e9d-418d-bd4d-000000077777"
        response = self.client.post(self.url, data=data, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LicencePayload.objects.count(), initial_licence_count + 1)

    @tag("1917", "update-fail")
    def test_post_update_fail_invalid_old_id(self):
        initial_licence_count = LicencePayload.objects.count()
        initial_licence_id_mapping_count = LicenceIdMapping.objects.count()

        data = self.licence_payload_json
        data["licence"]["id"] = "09e21356-9e9d-418d-bd4d-000000077777"
        data["licence"]["reference"] = "GBSIEL/2020/0000001/P/A"
        data["licence"]["old_id"] = "09e21356-9e9d-418d-bd4d-000000077777"
        data["licence"]["action"] = LicenceActionEnum.UPDATE
        response = self.client.post(self.url, data=self.licence_payload_json, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(LicencePayload.objects.count(), initial_licence_count)
        self.assertEqual(LicenceIdMapping.objects.count(), initial_licence_id_mapping_count)

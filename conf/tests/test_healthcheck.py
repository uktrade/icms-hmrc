import uuid
from datetime import timedelta

from django.conf import settings
from django.test import override_settings, testcases
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from conf.views import HealthCheck
from mail.enums import LicenceActionEnum, ReceptionStatusEnum
from mail.models import LicencePayload, Mail


class TestHealthcheck(testcases.TestCase):
    def setUp(self):
        self.url = reverse("healthcheck")

    def test_healthcheck_return_ok(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "OK")
        self.assertEqual(response.context["status"], status.HTTP_200_OK)

    @override_settings(CHIEF_SOURCE_SYSTEM="ILBDOTI")
    def test_healthcheck_return_ok_icms(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "OK")
        self.assertEqual(response.context["status"], status.HTTP_200_OK)

    def test_healthcheck_service_unavailable_pending_mail(self):
        sent_at = timezone.now() - timedelta(seconds=settings.EMAIL_AWAITING_REPLY_TIME)
        Mail.objects.create(
            edi_filename="filename",
            edi_data="1\\fileHeader\\CHIEF\\SPIRE\\",
            status=ReceptionStatusEnum.PENDING,
            sent_at=sent_at,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], HealthCheck.ERROR_PENDING_MAIL)
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_healthcheck_service_unavailable_pending_payload(self):
        received_at = timezone.now() - timedelta(seconds=settings.LICENSE_POLL_INTERVAL)
        LicencePayload.objects.create(
            icms_id=uuid.uuid4(),
            reference="ABC12345",
            action=LicenceActionEnum.INSERT,
            is_processed=False,
            received_at=received_at,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], HealthCheck.ERROR_PAYLOAD_OBJECTS)
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

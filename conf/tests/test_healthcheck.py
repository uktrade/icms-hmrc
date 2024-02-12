import uuid
from datetime import timedelta
from http import HTTPStatus

from django.conf import settings
from django.test import testcases
from django.urls import reverse
from django.utils import timezone

from mail.enums import LicenceActionEnum, MailStatusEnum
from mail.models import LicencePayload, Mail


class TestHealthcheck(testcases.TestCase):
    def setUp(self):
        self.url = reverse("healthcheck")

    def test_healthcheck_return_ok(self):
        response = self.client.get(self.url)

        self.assertContains(response, text="<status>OK</status>", status_code=HTTPStatus.OK)

    def test_healthcheck_service_unavailable_pending_mail(self):
        sent_at = timezone.now() - timedelta(seconds=settings.EMAIL_AWAITING_REPLY_TIME)
        Mail.objects.create(
            edi_filename="filename",
            edi_data="1\\fileHeader\\CHIEF\\SPIRE\\",
            status=MailStatusEnum.PENDING,
            sent_at=sent_at,
        )
        response = self.client.get(self.url)

        self.assertContains(
            response,
            text="<!--The following check failed: check_pending_mail-->",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )

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

        self.assertContains(
            response,
            text="<!--The following check failed: check_unprocessed_payloads-->",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )

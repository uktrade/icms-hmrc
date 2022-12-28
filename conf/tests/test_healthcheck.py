import uuid
from datetime import timedelta

from background_task.models import Task
from django.conf import settings
from django.test import testcases
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from mail.enums import LicenceActionEnum, ReceptionStatusEnum, ReplyStatusEnum
from mail.models import LicencePayload, Mail
from mail.tasks import LICENCE_DATA_TASK_QUEUE, MANAGE_INBOX_TASK_QUEUE


class TestHealthcheck(testcases.TestCase):
    def setUp(self):
        self.url = reverse("healthcheck")

    def test_healthcheck_return_ok(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "OK")
        self.assertEqual(response.context["status"], status.HTTP_200_OK)

    def test_healthcheck_service_unavailable_pending_mail(self):
        sent_at = timezone.now() - timedelta(seconds=settings.EMAIL_AWAITING_REPLY_TIME)
        Mail.objects.create(
            edi_filename="filename",
            edi_data="1\\fileHeader\\CHIEF\\SPIRE\\",
            status=ReplyStatusEnum.PENDING,
            sent_at=sent_at,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "Pending mail error")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_healthcheck_service_unavailable_pending_payload(self):
        received_at = timezone.now() - timedelta(seconds=settings.LICENSE_POLL_INTERVAL)
        LicencePayload.objects.create(
            lite_id=uuid.uuid4(),
            reference="ABC12345",
            action=LicenceActionEnum.INSERT,
            is_processed=False,
            received_at=received_at,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "Payload objects error")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_healthcheck_service_unavailable_inbox_task_not_responsive(self):
        run_at = timezone.now() + timedelta(minutes=settings.INBOX_POLL_INTERVAL)
        task, _ = Task.objects.get_or_create(queue=MANAGE_INBOX_TASK_QUEUE)
        task.run_at = run_at
        task.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "manage_inbox_queue error")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_healthcheck_service_unavailable_licence_update_task_not_responsive(self):
        run_at = timezone.now() + timedelta(minutes=settings.LITE_LICENCE_DATA_POLL_INTERVAL)
        task, _ = Task.objects.get_or_create(queue=LICENCE_DATA_TASK_QUEUE)
        task.run_at = run_at
        task.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "licences_updates_queue error")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

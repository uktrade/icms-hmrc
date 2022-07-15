from datetime import timedelta

from background_task.models import Task
from django.conf import settings
from django.test import testcases
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from mail.enums import ReceptionStatusEnum, ReplyStatusEnum
from mail.models import Mail
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
        self.assertEqual(response.context["message"], "not OK")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_healthcheck_service_unavailable_rejected_mail(self):
        sent_at = timezone.now() - timedelta(seconds=settings.EMAIL_AWAITING_CORRECTIONS_TIME)
        Mail.objects.create(
            edi_filename="filename",
            edi_data="1\\fileHeader\\CHIEF\\SPIRE\\",
            response_data="1\\line1\\rejected\\",
            status=ReceptionStatusEnum.REPLY_SENT,
            sent_at=sent_at,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "not OK")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_healthcheck_service_unavailable_inbox_task_not_responsive(self):
        run_at = timezone.now() + timedelta(minutes=settings.INBOX_POLL_INTERVAL)
        task, _ = Task.objects.get_or_create(queue=MANAGE_INBOX_TASK_QUEUE)
        task.run_at = run_at
        task.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "not OK")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_healthcheck_service_unavailable_licence_update_task_not_responsive(self):
        run_at = timezone.now() + timedelta(minutes=settings.LITE_LICENCE_DATA_POLL_INTERVAL)
        task, _ = Task.objects.get_or_create(queue=LICENCE_DATA_TASK_QUEUE)
        task.run_at = run_at
        task.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context["message"], "not OK")
        self.assertEqual(response.context["status"], status.HTTP_503_SERVICE_UNAVAILABLE)

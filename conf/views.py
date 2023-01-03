import datetime
import logging
import time

from background_task.models import Task
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.views import APIView

from mail.enums import ChiefSystemEnum, ReceptionStatusEnum, ReplyStatusEnum
from mail.models import LicencePayload, Mail
from mail.tasks import LICENCE_DATA_TASK_QUEUE, MANAGE_INBOX_TASK_QUEUE


class HealthCheck(APIView):
    ERROR_LICENCE_DATA_TASK_QUEUE = "licences_updates_queue error"
    ERROR_MANAGE_INBOX_TASK_QUEUE = "manage_inbox_queue error"
    ERROR_PENDING_MAIL = "Pending mail error"
    ERROR_REJECTED_MAIL = "Rejected mail error"
    ERROR_PAYLOAD_OBJECTS = "Payload objects error"

    def get(self, request):
        """
        Provides a health check endpoint as per [https://man.uktrade.io/docs/howtos/healthcheck.html#pingdom]
        """

        start_time = time.time()

        payload_object_pending = self._get_license_payload_object_pending()
        if payload_object_pending:
            logging.error(
                "Payload object has been unprocessed for over %s seconds: %s",
                settings.LICENSE_POLL_INTERVAL,
                payload_object_pending,
            )
            return self._build_response(HTTP_503_SERVICE_UNAVAILABLE, self.ERROR_PAYLOAD_OBJECTS, start_time)

        pending_mail = self._get_pending_mail()
        if pending_mail:
            logging.error(
                "The following Mail has been pending for over %s seconds: %s",
                settings.EMAIL_AWAITING_REPLY_TIME,
                pending_mail,
            )
            return self._build_response(HTTP_503_SERVICE_UNAVAILABLE, self.ERROR_PENDING_MAIL, start_time)

        if not self._is_lite_licence_update_task_responsive():
            logging.error("%s is not responsive", LICENCE_DATA_TASK_QUEUE)
            return self._build_response(HTTP_503_SERVICE_UNAVAILABLE, self.ERROR_LICENCE_DATA_TASK_QUEUE, start_time)

        if settings.CHIEF_SOURCE_SYSTEM == ChiefSystemEnum.SPIRE and not self._is_inbox_polling_task_responsive():
            logging.error("%s is not responsive", MANAGE_INBOX_TASK_QUEUE)
            return self._build_response(HTTP_503_SERVICE_UNAVAILABLE, self.ERROR_MANAGE_INBOX_TASK_QUEUE, start_time)

        logging.info("All services are responsive")
        return self._build_response(HTTP_200_OK, "OK", start_time)

    @staticmethod
    def _is_lite_licence_update_task_responsive() -> bool:
        dt = timezone.now() + datetime.timedelta(seconds=settings.LITE_LICENCE_DATA_POLL_INTERVAL)

        return Task.objects.filter(queue=LICENCE_DATA_TASK_QUEUE, run_at__lte=dt).exists()

    @staticmethod
    def _is_inbox_polling_task_responsive() -> bool:
        dt = timezone.now() + datetime.timedelta(seconds=settings.INBOX_POLL_INTERVAL)

        return Task.objects.filter(queue=MANAGE_INBOX_TASK_QUEUE, run_at__lte=dt).exists()

    @staticmethod
    def _get_pending_mail() -> []:
        dt = timezone.now() - datetime.timedelta(seconds=settings.EMAIL_AWAITING_REPLY_TIME)
        qs = Mail.objects.exclude(status=ReceptionStatusEnum.REPLY_SENT).filter(sent_at__lte=dt)

        return list(qs.values_list("id", flat=True))

    @staticmethod
    def _get_rejected_mail() -> []:
        dt = timezone.now() - datetime.timedelta(seconds=settings.EMAIL_AWAITING_CORRECTIONS_TIME)

        return list(
            Mail.objects.filter(
                status=ReceptionStatusEnum.REPLY_SENT,
                response_data__icontains=ReplyStatusEnum.REJECTED,
                sent_at__lte=dt,
            ).values_list("id", flat=True)
        )

    def _build_response(self, status, message, start_time):
        duration_ms = (time.time() - start_time) * 1000
        response_time = "{:.3f}".format(duration_ms)
        context = {"message": message, "response_time": response_time, "status": status}

        return render(self.request, "healthcheck.xml", context, content_type="application/xml", status=status)

    @staticmethod
    def _get_license_payload_object_pending() -> bool:
        dt = timezone.now() + datetime.timedelta(seconds=settings.LICENSE_POLL_INTERVAL)

        return LicencePayload.objects.filter(is_processed=False, received_at__lte=dt).first()

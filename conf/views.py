import datetime
import logging
import time

from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.views import APIView

from mail.enums import MailStatusEnum
from mail.models import LicencePayload, Mail


class HealthCheck(APIView):
    ERROR_PAYLOAD_OBJECTS = "Payload objects error"
    ERROR_PENDING_MAIL = "Pending mail error"

    def get(self, request):
        """Provides a health check endpoint as per [https://man.uktrade.io/docs/howtos/healthcheck.html#pingdom]"""

        start_time = time.time()

        payload_object_pending = self._get_license_payload_object_pending()
        if payload_object_pending:
            logging.error(
                "Payload object has been unprocessed for over %s seconds: %s",
                settings.LICENSE_POLL_INTERVAL,
                payload_object_pending,
            )
            return self._build_response(
                HTTP_503_SERVICE_UNAVAILABLE, self.ERROR_PAYLOAD_OBJECTS, start_time
            )

        pending_mail = self._get_pending_mail()
        if pending_mail:
            logging.error(
                "The following Mail has been pending for over %s seconds: %s",
                settings.EMAIL_AWAITING_REPLY_TIME,
                pending_mail,
            )
            return self._build_response(
                HTTP_503_SERVICE_UNAVAILABLE, self.ERROR_PENDING_MAIL, start_time
            )

        logging.info("All services are responsive")
        return self._build_response(HTTP_200_OK, "OK", start_time)

    @staticmethod
    def _get_license_payload_object_pending() -> bool:
        dt = timezone.now() + datetime.timedelta(seconds=settings.LICENSE_POLL_INTERVAL)

        return LicencePayload.objects.filter(is_processed=False, received_at__lte=dt).first()

    @staticmethod
    def _get_pending_mail() -> []:
        dt = timezone.now() - datetime.timedelta(seconds=settings.EMAIL_AWAITING_REPLY_TIME)
        qs = Mail.objects.exclude(status=MailStatusEnum.REPLY_PROCESSED).filter(sent_at__lte=dt)

        return list(qs.values_list("id", flat=True))

    def _build_response(self, status, message, start_time):
        duration_ms = (time.time() - start_time) * 1000
        response_time = "{:.3f}".format(duration_ms)
        context = {"message": message, "response_time": response_time, "status": status}

        return render(
            self.request, "healthcheck.xml", context, content_type="application/xml", status=status
        )

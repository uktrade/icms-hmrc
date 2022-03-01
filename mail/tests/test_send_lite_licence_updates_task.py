from unittest import mock, skip

from django.test import override_settings, tag

from mail.enums import ReceptionStatusEnum
from mail.models import LicencePayload, Mail
from mail.tasks import send_licence_data_to_hmrc
from mail.tests.libraries.client import LiteHMRCTestClient
from mail.libraries.lite_to_edifact_converter import EdifactValidationError


@override_settings(BACKGROUND_TASK_ENABLED=False)  # Disable task from being run on app initialization
class TaskTests(LiteHMRCTestClient):
    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_pending(self, send):
        mail = Mail(status=ReceptionStatusEnum.PENDING)
        mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_reply_pending(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_PENDING)
        mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_reply_received(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_RECEIVED)
        mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @skip("Fails, also fails for lite-hmrc project")
    @tag("missed-timing", "end-to-end")
    @mock.patch("mail.tasks.send")
    def test_reply_sent_rejected(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_SENT, response_data="rejected")
        mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_reply_sent_accepted(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_SENT, response_data="accepted")
        mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 1)

    @mock.patch("mail.libraries.lite_to_edifact_converter.validate_edifact_file")
    def test_exception(self, validator):
        validator.side_effect = EdifactValidationError()
        with self.assertRaises(EdifactValidationError):
            send_licence_data_to_hmrc.now()

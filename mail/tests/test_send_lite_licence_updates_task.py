from unittest import mock

from django.test import override_settings

from mail.enums import ReceptionStatusEnum
from mail.libraries.lite_to_edifact_converter import EdifactValidationError
from mail.models import LicencePayload, Mail
from mail.tasks import send_licence_data_to_hmrc
from mail.tests.libraries.client import LiteHMRCTestClient


@override_settings(BACKGROUND_TASK_ENABLED=False)  # Disable task from being run on app initialization
class TaskTests(LiteHMRCTestClient):
    def setUp(self):
        self.mail = Mail.objects.create(edi_filename="filename", edi_data="1\\fileHeader\\CHIEF\\SPIRE\\")
        super().setUp()

    @mock.patch("mail.tasks.send")
    def test_pending(self, send):
        self.mailstatus = ReceptionStatusEnum.PENDING
        self.mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @mock.patch("mail.tasks.send")
    def test_reply_pending(self, send):
        self.mail.status = ReceptionStatusEnum.REPLY_PENDING
        self.mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @mock.patch("mail.tasks.send")
    def test_reply_received(self, send):
        self.mail.status = ReceptionStatusEnum.REPLY_RECEIVED
        self.mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @mock.patch("mail.tasks.send")
    def test_reply_sent_rejected(self, send):
        self.mail.status = "reply_sent"
        self.mail.response_data = "rejected"
        self.mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 1)

    @mock.patch("mail.tasks.send")
    def test_reply_sent_accepted(self, send):
        self.mail.status = ReceptionStatusEnum.REPLY_SENT
        self.mail.response_data = "accepted"
        self.mail.save()
        send.return_value = None
        send_licence_data_to_hmrc.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 1)

    @mock.patch("mail.libraries.lite_to_edifact_converter.validate_edifact_file")
    def test_exception(self, validator):
        validator.side_effect = EdifactValidationError()
        with self.assertRaises(EdifactValidationError):
            self.mail.status = ReceptionStatusEnum.REPLY_SENT
            self.mail.save()
            send_licence_data_to_hmrc.now()

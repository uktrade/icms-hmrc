from unittest import mock

from django.test import tag

from mail.enums import ReceptionStatusEnum
from mail.models import LicencePayload, Mail
from mail.tasks import email_lite_licence_updates
from mail.tests.libraries.client import LiteHMRCTestClient


class TaskTests(LiteHMRCTestClient):
    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_pending(self, send):
        mail = Mail(status=ReceptionStatusEnum.PENDING)
        mail.save()
        send.return_value = None
        email_lite_licence_updates.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_reply_pending(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_PENDING)
        mail.save()
        send.return_value = None
        email_lite_licence_updates.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_reply_received(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_RECEIVED)
        mail.save()
        send.return_value = None
        email_lite_licence_updates.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @tag("missed-timing", "end-to-end")
    @mock.patch("mail.tasks.send")
    def test_reply_sent_rejected(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_SENT, response_data="rejected")
        mail.save()
        send.return_value = None
        email_lite_licence_updates.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 0)

    @tag("missed-timing")
    @mock.patch("mail.tasks.send")
    def test_reply_sent_accepted(self, send):
        mail = Mail(status=ReceptionStatusEnum.REPLY_SENT, response_data="accepted")
        mail.save()
        send.return_value = None
        email_lite_licence_updates.now()
        self.assertEqual(LicencePayload.objects.filter(is_processed=True).count(), 1)

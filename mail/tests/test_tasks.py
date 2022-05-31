import email.mime.multipart
from unittest import mock

from django.test import TestCase

from mail.tasks import get_lite_api_url, notify_users_of_rejected_mail


class GetLiteAPIUrlTests(TestCase):
    def test_get_url_with_no_path(self):
        with self.settings(LITE_API_URL="https://example.com"):
            result = get_lite_api_url()

        self.assertEqual(result, "https://example.com/licences/hmrc-integration/")

    def test_get_url_with_root_path(self):
        with self.settings(LITE_API_URL="https://example.com/"):
            result = get_lite_api_url()

        self.assertEqual(result, "https://example.com/licences/hmrc-integration/")

    def test_get_url_with_path_from_setting(self):
        with self.settings(LITE_API_URL="https://example.com/foo"):
            result = get_lite_api_url()

        self.assertEqual(result, "https://example.com/foo")


class NotifyUsersOfRejectedMailTests(TestCase):
    @mock.patch("smtplib.SMTP.send_message")
    def test_send_success(self, mock_send):
        settings = {
            "EMAIL_USER": "test@example.com",  # /PS-IGNORE
            "NOTIFY_USERS": ["notify@example.com"],  # /PS-IGNORE
        }
        with self.settings(**settings):
            notify_users_of_rejected_mail.now("123", "1999-12-31 23:45:59")

        self.assertEqual(len(mock_send.call_args_list), 1)
        message = mock_send.call_args[0][0]
        self.assertIsInstance(message, email.mime.multipart.MIMEMultipart)

        expected_headers = {
            "Content-Type": "multipart/mixed",
            "MIME-Version": "1.0",
            "From": "test@example.com",  # /PS-IGNORE
            "To": "notify@example.com",  # /PS-IGNORE
            "Subject": "Mail rejected",
        }
        self.assertDictEqual(dict(message), expected_headers)

        text_payload = message.get_payload(0)
        expected_body = "Mail [123] received at [1999-12-31 23:45:59] was rejected"
        self.assertEqual(text_payload.get_payload(), expected_body)

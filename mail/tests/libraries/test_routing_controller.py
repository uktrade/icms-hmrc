import unittest
from unittest.mock import patch

from django.test import override_settings

from mail.libraries.routing_controller import (
    get_hmrc_to_dit_mailserver,
    get_mock_hmrc_mailserver,
    get_spire_to_dit_mailserver,
)


class RoutingControllerTest(unittest.TestCase):
    @patch("mail.libraries.routing_controller.BasicAuthentication")
    @patch("mail.libraries.routing_controller.MailServer")
    @override_settings(
        INCOMING_EMAIL_USER="incoming.email.user@example.com",
        INCOMING_EMAIL_PASSWORD="shhh",
        INCOMING_EMAIL_HOSTNAME="host.example.com",
        INCOMING_EMAIL_POP3_PORT="123",
    )
    def test_get_spire_to_dit_mailserver(self, mock_MailServer, mock_BasicAuthentication):
        spire_to_dit_mailserver = get_spire_to_dit_mailserver()

        mock_BasicAuthentication.asset_called_with(
            user="incoming.email.user@example.com",
            password="shhh",
        )
        mock_MailServer.assert_called_with(
            mock_BasicAuthentication(),
            hostname="host.example.com",
            pop3_port="123",
        )

        self.assertEqual(spire_to_dit_mailserver, mock_MailServer())

    @patch("mail.libraries.routing_controller.BasicAuthentication")
    @patch("mail.libraries.routing_controller.MailServer")
    @override_settings(
        HMRC_TO_DIT_EMAIL_USER="hmrc.to.dit.email.user@example.com",
        HMRC_TO_DIT_EMAIL_PASSWORD="shhh",
        HMRC_TO_DIT_EMAIL_HOSTNAME="host.example.com",
        HMRC_TO_DIT_EMAIL_POP3_PORT="123",
    )
    def test_get_hmrc_to_dit_mailserver(self, mock_MailServer, mock_BasicAuthentication):
        hmrc_to_dit_mailserver = get_hmrc_to_dit_mailserver()

        mock_BasicAuthentication.asset_called_with(
            user="hmrc.to.dit.email.user@example.com",
            password="shhh",
        )
        mock_MailServer.assert_called_with(
            mock_BasicAuthentication(),
            hostname="host.example.com",
            pop3_port="123",
        )

        self.assertEqual(hmrc_to_dit_mailserver, mock_MailServer())

    @patch("mail.libraries.routing_controller.BasicAuthentication")
    @patch("mail.libraries.routing_controller.MailServer")
    @override_settings(
        MOCK_HMRC_EMAIL_USER="mock.hmrc.email.user@example.com",
        MOCK_HMRC_EMAIL_PASSWORD="shhh",
        MOCK_HMRC_EMAIL_HOSTNAME="host.example.com",
        MOCK_HMRC_EMAIL_POP3_PORT="123",
    )
    def test_get_mock_hmrc_mailserver(self, mock_MailServer, mock_BasicAuthentication):
        mock_hmrc_mailserver = get_mock_hmrc_mailserver()

        mock_BasicAuthentication.asset_called_with(
            user="hmrc.to.dit.email.user@example.com",
            password="shhh",
        )
        mock_MailServer.assert_called_with(
            mock_BasicAuthentication(),
            hostname="host.example.com",
            pop3_port="123",
        )

        self.assertEqual(mock_hmrc_mailserver, mock_MailServer())

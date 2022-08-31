import unittest
from unittest.mock import patch

from django.test import override_settings

from mail.auth import BasicAuthentication, ModernAuthentication
from mail.libraries.routing_controller import (
    get_hmrc_to_dit_mailserver,
    get_mock_hmrc_mailserver,
    get_spire_to_dit_mailserver,
)


class RoutingControllerTest(unittest.TestCase):
    @patch(
        "mail.libraries.routing_controller.ModernAuthentication",
        spec=ModernAuthentication,
    )
    @patch("mail.libraries.routing_controller.MailServer")
    @override_settings(
        INCOMING_EMAIL_USER="incoming.email.user@example.com",
        INCOMING_EMAIL_HOSTNAME="host.example.com",
        INCOMING_EMAIL_POP3_PORT="123",
        AZURE_AUTH_CLIENT_ID="azure-auth-client-id",
        AZURE_AUTH_CLIENT_SECRET="azure-auth-client-secret",  # nosec
        AZURE_AUTH_TENANT_ID="azure-auth-tenant-id",
    )
    def test_get_spire_to_dit_mailserver(self, mock_MailServer, mock_ModernAuthentication):
        spire_to_dit_mailserver = get_spire_to_dit_mailserver()

        mock_ModernAuthentication.assert_called_with(
            user="incoming.email.user@example.com",
            client_id="azure-auth-client-id",
            client_secret="azure-auth-client-secret",  # nosec
            tenant_id="azure-auth-tenant-id",
        )
        mock_MailServer.assert_called_with(
            mock_ModernAuthentication(),
            hostname="host.example.com",
            pop3_port="123",
        )

        self.assertEqual(spire_to_dit_mailserver, mock_MailServer())

    @patch(
        "mail.libraries.routing_controller.ModernAuthentication",
        spec=ModernAuthentication,
    )
    @patch("mail.libraries.routing_controller.MailServer")
    @override_settings(
        HMRC_TO_DIT_EMAIL_USER="hmrc.to.dit.email.user@example.com",
        HMRC_TO_DIT_EMAIL_HOSTNAME="host.example.com",
        HMRC_TO_DIT_EMAIL_POP3_PORT="123",
        AZURE_AUTH_CLIENT_ID="azure-auth-client-id",
        AZURE_AUTH_CLIENT_SECRET="azure-auth-client-secret",  # nosec
        AZURE_AUTH_TENANT_ID="azure-auth-tenant-id",
    )
    def test_get_hmrc_to_dit_mailserver(self, mock_MailServer, mock_ModernAuthentication):
        hmrc_to_dit_mailserver = get_hmrc_to_dit_mailserver()

        mock_ModernAuthentication.assert_called_with(
            user="hmrc.to.dit.email.user@example.com",
            client_id="azure-auth-client-id",
            client_secret="azure-auth-client-secret",  # nosec
            tenant_id="azure-auth-tenant-id",
        )
        mock_MailServer.assert_called_with(
            mock_ModernAuthentication(),
            hostname="host.example.com",
            pop3_port="123",
        )

        self.assertEqual(hmrc_to_dit_mailserver, mock_MailServer())

    @patch(
        "mail.libraries.routing_controller.BasicAuthentication",
        spec=BasicAuthentication,
    )
    @patch("mail.libraries.routing_controller.MailServer")
    @override_settings(
        MOCK_HMRC_EMAIL_USER="mock.hmrc.email.user@example.com",
        MOCK_HMRC_EMAIL_PASSWORD="shhh",  # nosec
        MOCK_HMRC_EMAIL_HOSTNAME="host.example.com",
        MOCK_HMRC_EMAIL_POP3_PORT="123",
    )
    def test_get_mock_hmrc_mailserver(self, mock_MailServer, mock_BasicAuthentication):
        mock_hmrc_mailserver = get_mock_hmrc_mailserver()

        mock_BasicAuthentication.assert_called_with(
            user="mock.hmrc.email.user@example.com",
            password="shhh",  # nosec
        )
        mock_MailServer.assert_called_with(
            mock_BasicAuthentication(),
            hostname="host.example.com",
            pop3_port="123",
        )

        self.assertEqual(mock_hmrc_mailserver, mock_MailServer())

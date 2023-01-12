import base64
from poplib import POP3_SSL
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from mail.auth import BasicAuthentication, ModernAuthentication


class BasicAuthenticationTests(SimpleTestCase):
    def test_authenticates_connection(self):
        pop3conn = MagicMock(spec=POP3_SSL)
        mock_conn = pop3conn()

        auth = BasicAuthentication("user", "password")
        auth.authenticate(mock_conn)
        mock_conn.user.assert_called_with("user")
        mock_conn.pass_.assert_called_with("password")

    def test_equal(self):
        auth = BasicAuthentication("user", "password")
        equal_auth = BasicAuthentication("user", "password")

        self.assertEqual(auth, equal_auth)

    def test_not_equal(self):
        auth = BasicAuthentication("user", "password")
        equal_auth = BasicAuthentication("diff_user", "diff_password")

        self.assertNotEqual(auth, equal_auth)


class ModernAuthenticationTests(SimpleTestCase):
    def test_authenticates_connection_with_silent_acquisition(self):
        pop3conn = MagicMock(spec=POP3_SSL)
        mock_conn = pop3conn()

        username = "username"
        client_id = "client_id"
        client_secret = "client_secret"  # nosec
        tenant_id = "tenant_id"

        mock_access_token = {
            "access_token": "access_token",
        }

        with patch("mail.auth.msal") as mock_msal:
            mock_ConfidentialClientApplication = mock_msal.ConfidentialClientApplication()  # noqa: N806
            mock_acquire_token_silent = mock_ConfidentialClientApplication.acquire_token_silent
            mock_acquire_token_silent.return_value = mock_access_token

            auth = ModernAuthentication(
                username,
                client_id,
                client_secret,
                tenant_id,
            )
            auth.authenticate(mock_conn)

        mock_msal.ConfidentialClientApplication.assert_called_with(
            client_id,
            authority="https://login.microsoftonline.com/tenant_id",
            client_credential="client_secret",
        )

        mock_acquire_token_silent.assert_called_with(
            ["https://outlook.office.com/.default"],
            account=None,
        )

        access_string = base64.b64encode("user=username\x01auth=Bearer access_token\x01\x01".encode()).decode()
        mock_conn._shortcmd.assert_has_calls(
            [
                call("AUTH XOAUTH2"),
                call(access_string),
            ]
        )

    def test_authenticates_connection_without_silent_acquisition(self):
        pop3conn = MagicMock(spec=POP3_SSL)
        mock_conn = pop3conn()

        username = "username"
        client_id = "client_id"
        client_secret = "client_secret"  # nosec
        tenant_id = "tenant_id"

        mock_access_token = {
            "access_token": "access_token",
        }

        with patch("mail.auth.msal") as mock_msal:
            mock_ConfidentialClientApplication = mock_msal.ConfidentialClientApplication()  # noqa: N806

            mock_acquire_token_silent = mock_ConfidentialClientApplication.acquire_token_silent
            mock_acquire_token_silent.return_value = None

            mock_acquire_token_for_client = mock_ConfidentialClientApplication.acquire_token_for_client
            mock_acquire_token_for_client.return_value = mock_access_token

            auth = ModernAuthentication(
                username,
                client_id,
                client_secret,
                tenant_id,
            )
            auth.authenticate(mock_conn)

        mock_msal.ConfidentialClientApplication.assert_called_with(
            client_id,
            authority="https://login.microsoftonline.com/tenant_id",
            client_credential="client_secret",
        )

        mock_acquire_token_silent.assert_called_with(
            ["https://outlook.office.com/.default"],
            account=None,
        )
        mock_acquire_token_for_client.assert_called_with(
            scopes=["https://outlook.office.com/.default"],
        )

        access_string = base64.b64encode("user=username\x01auth=Bearer access_token\x01\x01".encode()).decode()
        mock_conn._shortcmd.assert_has_calls(
            [
                call("AUTH XOAUTH2"),
                call(access_string),
            ]
        )

    def test_equal(self):
        username = "username"
        client_id = "client_id"
        client_secret = "client_secret"  # nosec
        tenant_id = "tenant_id"

        with patch("mail.auth.msal"):
            auth = ModernAuthentication(
                username,
                client_id,
                client_secret,
                tenant_id,
            )
            equal_auth = ModernAuthentication(
                username,
                client_id,
                client_secret,
                tenant_id,
            )

        self.assertEqual(auth, equal_auth)

    def test_not_equal(self):
        with patch("mail.auth.msal"):
            auth = ModernAuthentication(
                "username",
                "client_id",
                "client_secret",
                "tenant_id",
            )
            equal_auth = ModernAuthentication(
                "other_username",
                "other_client_id",
                "other_client_secret",
                "other_tenant_id",
            )

        self.assertNotEqual(auth, equal_auth)

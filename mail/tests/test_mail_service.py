from poplib import POP3_SSL
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from mail.auth import Authenticator
from mail.servers import MailServer


class MailServerTests(SimpleTestCase):
    def test_mail_server_equal(self):
        auth = Mock(spec=Authenticator)

        m1 = MailServer(auth, hostname="host", pop3_port=1)  # nosec
        m2 = MailServer(auth, hostname="host", pop3_port=1)  # nosec

        self.assertEqual(m1, m2)

    def test_mail_server_not_equal(self):
        auth = Mock(spec=Authenticator)

        m1 = MailServer(auth, hostname="host", pop3_port=1)  # nosec
        m2 = MailServer(auth, hostname="host", pop3_port=2)  # nosec

        self.assertNotEqual(m1, m2)

        auth = Mock(spec=Authenticator)

        m1 = MailServer(auth, hostname="host", pop3_port=1)  # nosec
        m2 = Mock()  # nosec

        self.assertNotEqual(m1, m2)

    def test_mail_server_connect_to_pop3(self):
        hostname = "host"
        pop3_port = 1

        auth = Mock(spec=Authenticator)
        pop3conn = MagicMock(spec=POP3_SSL)

        with patch("mail.servers.poplib") as mock_poplib:
            mock_poplib.POP3_SSL = pop3conn

            mail_server = MailServer(
                auth,
                hostname=hostname,
                pop3_port=pop3_port,
            )
            mail_server.connect_to_pop3()

        pop3conn.assert_called_with(
            hostname,
            pop3_port,
            timeout=60,
        )

        mock_connection = pop3conn()
        auth.authenticate.assert_called_with(mock_connection)

    def test_mail_server_quit_pop3_connection(self):
        hostname = "host"
        pop3_port = 1

        auth = Mock(spec=Authenticator)
        pop3conn = MagicMock(spec=POP3_SSL)

        with patch("mail.servers.poplib") as mock_poplib:
            mock_poplib.POP3_SSL = pop3conn

            mail_server = MailServer(
                auth,
                hostname=hostname,
                pop3_port=pop3_port,
            )
            mail_server.connect_to_pop3()
            mail_server.quit_pop3_connection()

        mock_connection = pop3conn()
        mock_connection.quit.assert_called_once()

    def test_mail_server_user(self):
        auth = Mock(spec=Authenticator)
        auth.user = Mock()
        mail_server = MailServer(
            auth,
            hostname="host",
            pop3_port=1,
        )
        self.assertEqual(mail_server.user, auth.user)

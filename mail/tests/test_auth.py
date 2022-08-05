from poplib import POP3_SSL
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from mail.auth import BasicAuthentication


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

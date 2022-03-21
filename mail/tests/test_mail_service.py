from collections import OrderedDict
from poplib import POP3_SSL
from unittest.mock import MagicMock

from django.test import SimpleTestCase
from parameterized import parameterized

from mail.libraries.mailbox_service import read_last_message, read_last_three_emails, get_message_iterator
from mail.servers import MailServer
from mail.tests.libraries.client import LiteHMRCTestClient


class MailServiceTests(LiteHMRCTestClient):
    @parameterized.expand(
        [
            (
                [b"1 1234"],
                {b"1": [b"OK", [b"Subject: mock", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"], "\r\n.\r\n"]},
            ),
            (
                [b"0 1234"],
                {b"0": [b"OK", [b"Subject: mock", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"], "\r\n.\r\n"]},
            ),
            (
                [b"0 1234", b"1 4321"],
                {
                    b"0": [b"OK", [b"Subject: mock", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"], "\r\n.\r\n"],
                    b"1": [b"OK", [b"Subject: mock", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"], "\r\n.\r\n"],
                },
            ),
        ]
    )
    def test_read_last_message(self, email_list, retr_data):
        pop3conn = MagicMock(spec=POP3_SSL)
        pop3conn.list.return_value = (None, email_list, None)
        pop3conn.retr = MagicMock(side_effect=retr_data.__getitem__)
        message = read_last_message(pop3conn)
        self.assertEqual(message.subject, "mock")
        message_id = email_list[-1].split()[0]
        pop3conn.retr.assert_called_once_with(message_id)

    @parameterized.expand(
        [
            (
                [b"0 1234", b"1 4321"],
                OrderedDict(
                    {
                        "0": [
                            b"OK",
                            [b"Subject: mock0", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                        "1": [
                            b"OK",
                            [b"Subject: mock1", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                    }
                ),
            ),
            (
                [b"0 1234", b"1 4321", b"4 4444"],
                OrderedDict(
                    {
                        "0": [
                            b"OK",
                            [b"Subject: mock0", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                        "1": [
                            b"OK",
                            [b"Subject: mock1", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                        "4": [
                            b"OK",
                            [b"Subject: mock4", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                    }
                ),
            ),
            (
                [b"2 1234", b"1 4321", b"4 4444", b"5 5555"],
                OrderedDict(
                    {
                        "2": [
                            b"OK",
                            [b"Subject: mock2", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                        "1": [
                            b"OK",
                            [b"Subject: mock1", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                        "4": [
                            b"OK",
                            [b"Subject: mock4", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                        "5": [
                            b"OK",
                            [b"Subject: mock5", b"Date: Mon, 17 May 2021 14:20:18 +0100", b"hello"],
                            "\r\n.\r\n",
                        ],
                    }
                ),
            ),
        ]
    )
    def test_read_last_three_emails(self, email_list, retr_data):
        pop3conn = MagicMock(spec=POP3_SSL)
        pop3conn.list.return_value = (None, email_list, None)
        pop3conn.retr = MagicMock(side_effect=retr_data.__getitem__)
        message_list = read_last_three_emails(pop3conn)

        # check it only gets up to 3 messages
        self.assertEqual(len(message_list), min(len(email_list), 3))

        # check they are the last 3 messages (reverse input order and take first 3)
        message_list_and_expected_source = zip(message_list, reversed(retr_data.values()))
        for message, retr_item in message_list_and_expected_source:
            self.assertEqual(f"Subject: {message.subject}".encode("utf-8"), retr_item[1][0])


class MailServerTests(SimpleTestCase):
    def test_mail_server_equal(self):
        m1 = MailServer(hostname="host", user="u", password="p", pop3_port=1, smtp_port=2)  # nosec

        m2 = MailServer(hostname="host", user="u", password="p", pop3_port=1, smtp_port=2)  # nosec

        self.assertEqual(m1, m2)

    def test_mail_server_not_equal(self):
        m1 = MailServer(hostname="host", user="u", password="p", pop3_port=1, smtp_port=2)  # nosec

        m2 = MailServer(hostname="host", user="u", password="p", pop3_port=2, smtp_port=1)  # nosec

        self.assertNotEqual(m1, m2)

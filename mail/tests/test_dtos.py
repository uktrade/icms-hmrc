from unittest.mock import Mock, patch

from dateutil.parser import parse
from django.test import SimpleTestCase
from parameterized import parameterized

from mail.libraries.email_message_dto import *
from mail.libraries.helpers import read_file, sort_dtos_by_date, to_mail_message_dto
from mail.libraries.routing_controller import get_email_message_dtos
from mail.servers import MailServer
from mail.tests.libraries.client import LiteHMRCTestClient


class TestDtos(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

    def test_EmailMessageDto(self):
        email_message_dto = EmailMessageDto(
            run_number=101,
            sender="test@example.com",
            receiver="receiver@example.com",
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="body",
            subject="subject",
            attachment=[],
            raw_data="qwerty",
        )
        self.assertEqual(101, email_message_dto.run_number, "Run-number did not match")
        self.assertEqual("test@example.com", email_message_dto.sender, "sender email did not match")
        self.assertEqual(
            "receiver@example.com",
            email_message_dto.receiver,
            "receiver email did not match",
        )

    @parameterized.expand(
        [
            (
                [
                    "Tue, 25 May 2021 10:12:10 +0100 (BST)",
                    "Mon, 18 May 2021 10:12:10 +0100",
                    "Wed, 20 Jan 2021 15:15:15 +0400",
                ],
                ["2021-01-20T15:15:15+04:00", "2021-05-18T10:12:10+01:00", "2021-05-25T10:12:10+01:00"],
            ),
        ]
    )
    def test_sorting_of_dtos_by_date(self, dates_before, expected):
        input_dtos = []
        for index, item in enumerate(dates_before, start=1):
            dt = parse(item)
            input_dtos.append(
                (
                    EmailMessageDto(
                        run_number=index,
                        date=dt,
                        sender="",
                        receiver="",
                        subject="",
                        body=None,
                        attachment=[],
                        raw_data="",
                    ),
                    lambda x: x,
                )
            )

        sorted_list = [item[0].date.isoformat() for item in sort_dtos_by_date(input_dtos)]
        self.assertEqual(sorted_list, expected)


class TestKnownMessageToDTO(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.batched_licence_data_email = [
            None,
            read_file("mail/tests/files/batched_licence_data.email", mode="rb").splitlines(),
            None,
        ]

    def test_multi_licence_message_from_spire(self):
        mail_message = to_mail_message_dto(self.batched_licence_data_email)
        self.assertEqual(mail_message.run_number, 96838)
        self.assertEqual(mail_message.receiver, "test-test-gateway@test.trade.gov.uk")


class TestGetEmailMessagesDTOs(SimpleTestCase):
    @patch("mail.libraries.routing_controller.get_message_iterator")
    def test_get_email_message_dtos(self, mock_get_message_iterator):
        mock_mail_server = Mock(spec=MailServer)
        mock_emails = [Mock(), Mock()]
        mock_get_message_iterator.return_value = mock_emails

        emails = get_email_message_dtos(mock_mail_server)

        self.assertEqual(emails, mock_emails)
        mock_mail_server.connect_to_pop3.assert_called_once_with()
        mock_get_message_iterator.assert_called_once_with(
            mock_mail_server.connect_to_pop3(),
            mock_mail_server.user,
        )
        mock_mail_server.quit_pop3_connection.assert_called_once_with()

from django.test import SimpleTestCase, tag

from mail.libraries.email_message_dto import *
from mail.libraries.helpers import read_file, to_mail_message_dto
from mail.tests.libraries.client import LiteHMRCTestClient


class TestDtos(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

    def test_EmailMessageDto(self):
        email_message_dto = EmailMessageDto(
            run_number=101,
            sender="test@example.com",
            receiver="receiver@example.com",
            body="body",
            subject="subject",
            attachment=[],
            raw_data="qwerty",
        )
        self.assertEqual(101, email_message_dto.run_number, "Run-number did not match")
        self.assertEqual("test@example.com", email_message_dto.sender, "sender email did not match")
        self.assertEqual(
            "receiver@example.com", email_message_dto.receiver, "receiver email did not match",
        )


@tag("mail_parse")
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

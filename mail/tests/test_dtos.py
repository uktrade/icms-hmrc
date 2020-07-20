from mail.libraries.email_message_dto import *
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

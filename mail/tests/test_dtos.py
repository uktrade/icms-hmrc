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

    def test_toJson(self):
        attachement_data = b"a line"
        email_message_dto = EmailMessageDto(
            run_number=101,
            sender="test@example.com",
            receiver="receiver@example.com",
            body="body",
            subject="subject",
            attachment=["filename", attachement_data],
            raw_data="qwerty",
        )
        dto_in_json = to_json(email_message_dto)
        dto_in_dict = json.loads(dto_in_json)
        self.assertEqual(dto_in_dict["run_number"], 101)
        self.assertEqual(dto_in_dict["body"], "body")
        self.assertEqual(dto_in_dict["attachment"]["name"], "filename")
        self.assertEqual(dto_in_dict["attachment"]["data"], "a line")

    def test_toJson_raiseTypeError(self):
        email_message_dto = EmailMessageDto(
            run_number=101,
            sender="test@example.com",
            receiver="receiver@example.com",
            body="body",
            subject="subject",
            attachment=["filename", "contents not encoded"],
            raw_data="qwerty",
        )
        with self.assertRaises(TypeError) as context:
            to_json(email_message_dto)
        self.assertEqual("Invalid attribute 'attachment'", str(context.exception))

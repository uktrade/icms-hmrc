import logging
from django.test import tag
from conf.settings import SPIRE_ADDRESS, HMRC_ADDRESS
from mail.dtos import EmailMessageDto
from mail.services.data_processors import (
    to_email_message_dto_from,
    serialize_email_message,
)
from mail.tests.data_processors_test_base import DataProcessorsTestBase

logger = logging.getLogger(__name__)


class SerializeEmailMessageTests(DataProcessorsTestBase):
    def setUp(self):
        super().setUp()

    def test_successful_usage_update_inbound_dto_converts_to_outbound_dto(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=HMRC_ADDRESS,
            receiver="receiver@example.com",
            body="body",
            subject=self.licence_usage_file_name,
            attachment=[self.licence_usage_file_name, self.licence_usage_file_body,],
            raw_data="qwerty",
        )

        # dto to dto processing
        mail = serialize_email_message(email_message_dto)
        dto = to_email_message_dto_from(mail)

        self.assertEqual(dto.run_number, self.usage_update.spire_run_number + 1)
        self.assertEqual(dto.sender, HMRC_ADDRESS)
        self.assertEqual(dto.attachment[0], email_message_dto.attachment[0])
        self.assertIn(
            dto.attachment[1], str(email_message_dto.attachment[1]),
        )
        self.assertEqual(dto.subject, self.licence_usage_file_name)
        self.assertEqual(dto.receiver, SPIRE_ADDRESS)
        self.assertEqual(dto.body, None)
        self.assertEqual(dto.raw_data, None)

    def test_unsuccessful_inbound_dto_does_not_convert_to_outbound_dto(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender="test@general.com",
            receiver="receiver@example.com",
            body="body",
            subject=self.licence_usage_file_name,
            attachment=[self.licence_usage_file_name, self.licence_usage_file_body],
            raw_data="qwerty",
        )

        self.assertEqual(serialize_email_message(email_message_dto), False)

    def test_licence_update_dto_to_dto(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=SPIRE_ADDRESS,
            receiver=HMRC_ADDRESS,
            body=None,
            subject=self.licence_update_file_name,
            attachment=[self.licence_update_file_name, self.licence_update_reply_body,],
            raw_data="qwerty",
        )

        # dto to dto processing
        mail = serialize_email_message(email_message_dto)
        dto = to_email_message_dto_from(mail)

        self.assertEqual(dto.run_number, self.licence_update.hmrc_run_number + 1)
        self.assertEqual(dto.sender, SPIRE_ADDRESS)
        self.assertEqual(dto.attachment[0], email_message_dto.attachment[0])
        self.assertIn(
            dto.attachment[1], str(email_message_dto.attachment[1]),
        )
        self.assertEqual(dto.subject, self.licence_update_file_name)
        self.assertEqual(dto.receiver, HMRC_ADDRESS)
        self.assertEqual(dto.body, None)
        self.assertEqual(dto.raw_data, None)

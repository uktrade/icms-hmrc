from django.test import tag
from rest_framework.exceptions import ValidationError

from django.conf import settings
from mail.libraries.data_processors import (
    to_email_message_dto_from,
    serialize_email_message,
)
from mail.libraries.email_message_dto import EmailMessageDto
from mail.tests.libraries.data_processors_base import DataProcessorsTestBase


class SerializeEmailMessageTests(DataProcessorsTestBase):
    @tag("ser")
    def test_successful_usage_update_inbound_dto_converts_to_outbound_dto(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=settings.HMRC_ADDRESS,
            receiver="receiver@example.com",
            body="body",
            subject=self.licence_usage_file_name,
            attachment=[self.licence_usage_file_name, self.licence_usage_file_body],
            raw_data="qwerty",
        )

        # dto to dto processing
        mail = serialize_email_message(email_message_dto)
        dto = to_email_message_dto_from(mail)

        self.assertEqual(dto.run_number, self.usage_update.hmrc_run_number + 1)
        self.assertEqual(dto.sender, settings.HMRC_ADDRESS)
        self.assertEqual(dto.receiver, settings.SPIRE_ADDRESS)
        self.assertEqual(dto.body, None)
        self.assertEqual(dto.raw_data, None)

    @tag("ser")
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

        self.assertRaises(ValidationError, serialize_email_message, email_message_dto)

    @tag("ser")
    def test_licence_data_dto_to_dto(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=settings.SPIRE_ADDRESS,
            receiver=settings.HMRC_ADDRESS,
            body=None,
            subject=self.licence_data_file_name,
            attachment=[self.licence_data_file_name, self.licence_data_file_body,],
            raw_data="qwerty",
        )

        # dto to dto processing
        mail = serialize_email_message(email_message_dto)
        dto = to_email_message_dto_from(mail)

        self.assertEqual(dto.run_number, self.licence_data.hmrc_run_number + 1)
        self.assertEqual(dto.sender, settings.EMAIL_USER)
        self.assertEqual(dto.attachment[0], "ILBDOTI_live_CHIEF_licenceData_29_201902080025")
        self.assertEqual(dto.subject, "ILBDOTI_live_CHIEF_licenceData_29_201902080025")
        self.assertEqual(dto.receiver, settings.HMRC_ADDRESS)
        self.assertEqual(dto.body, None)
        self.assertEqual(dto.raw_data, None)

from django.test import tag

from conf.settings import SPIRE_ADDRESS, HMRC_ADDRESS, EMAIL_USER
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
            sender=HMRC_ADDRESS,
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
        self.assertEqual(dto.sender, HMRC_ADDRESS)
        self.assertEqual(dto.receiver, SPIRE_ADDRESS)
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

        self.assertEqual(serialize_email_message(email_message_dto), None)

    @tag("ser")
    def test_licence_update_dto_to_dto(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=SPIRE_ADDRESS,
            receiver=HMRC_ADDRESS,
            body=None,
            subject=self.licence_update_file_name,
            attachment=[self.licence_update_file_name, self.licence_update_file_body,],
            raw_data="qwerty",
        )

        # dto to dto processing
        mail = serialize_email_message(email_message_dto)
        dto = to_email_message_dto_from(mail)

        self.assertEqual(dto.run_number, self.licence_update.hmrc_run_number + 1)
        self.assertEqual(dto.sender, EMAIL_USER)
        self.assertEqual(dto.attachment[0], "ILBDOTI_live_CHIEF_licenceUpdate_29_201902080025")
        self.assertEqual(dto.subject, "ILBDOTI_live_CHIEF_licenceUpdate_29_201902080025")
        self.assertEqual(dto.receiver, HMRC_ADDRESS)
        self.assertEqual(dto.body, None)
        self.assertEqual(dto.raw_data, None)

from django.test import tag
from conf.settings import SPIRE_ADDRESS, HMRC_ADDRESS
from mail.dtos import EmailMessageDto
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.services.data_processors import (
    to_email_message_dto_from,
    serialize_email_message,
)
from mail.tests.test_helpers import print_all_mails
from mail.tests.data_processors_test_base import DataProcessorsTestBase


class MailToMailMessageDtoTests(DataProcessorsTestBase):
    def test_convert_licence_reply_mail_message_dto(self):
        # update test mail as reply pending
        self.mail.status = ReceptionStatusEnum.REPLY_PENDING
        self.mail.extract_type = ExtractTypeEnum.LICENCE_UPDATE
        self.mail.save()
        print_all_mails()

        # create dto for license reply email
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=HMRC_ADDRESS,
            receiver="receiver@example.com",
            body=None,
            subject=self.licence_update_reply_name,
            attachment=[
                self.licence_update_reply_name,
                self.licence_update_reply_body,
            ],
            raw_data="qwerty",
        )

        _mail = serialize_email_message(email_message_dto)
        reply_mail_message_dto = to_email_message_dto_from(_mail)

        self.assertEqual(
            reply_mail_message_dto.run_number, self.licence_update.source_run_number
        )
        self.assertEqual(reply_mail_message_dto.sender, HMRC_ADDRESS)
        self.assertEqual(
            reply_mail_message_dto.attachment[0], email_message_dto.attachment[0]
        )
        self.assertIn(
            reply_mail_message_dto.attachment[1], str(email_message_dto.attachment[1]),
        )
        self.assertEqual(reply_mail_message_dto.subject, email_message_dto.subject)
        self.assertEqual(reply_mail_message_dto.receiver, SPIRE_ADDRESS)
        self.assertEqual(reply_mail_message_dto.body, None)
        self.assertEqual(reply_mail_message_dto.raw_data, None)

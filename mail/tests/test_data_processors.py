import logging
from conf.settings import SPIRE_ADDRESS, HMRC_ADDRESS
from conf.test_client import LiteHMRCTestClient
from mail.dtos import EmailMessageDto
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.models import Mail, LicenceUpdate, UsageUpdate
from mail.services.data_processors import (
    serialize_email_message,
    to_email_message_dto_from,
)
from mail.services.logging_decorator import lite_log
from mail.tests.test_helpers import print_all_mails

logger = logging.getLogger(__name__)


class TestDataProcessors(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

        self.hmrc_run_number = 28
        self.source_run_number = 15
        self.mail = Mail.objects.create(
            edi_data=self.licence_usage_file_body,
            extract_type=ExtractTypeEnum.USAGE_UPDATE,
            status=ReceptionStatusEnum.REPLY_SENT,
            edi_filename=self.licence_usage_file_name,
        )

        self.licence_update = LicenceUpdate.objects.create(
            mail=self.mail,
            hmrc_run_number=self.hmrc_run_number,
            source_run_number=self.source_run_number,
            source=SourceEnum.SPIRE,
        )

        self.usage_update = UsageUpdate.objects.create(
            mail=self.mail,
            spire_run_number=self.source_run_number,
            hmrc_run_number=self.hmrc_run_number,
        )

    def test_mail_data_serialized_successfully(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number,
            sender=HMRC_ADDRESS,
            receiver=SPIRE_ADDRESS,
            body="body",
            subject=self.licence_usage_file_name,
            attachment=[self.licence_usage_file_name, self.licence_usage_file_body],
            raw_data="",
        )

        serialize_email_message(email_message_dto)

        email = Mail.objects.valid().last()
        usage_update = UsageUpdate.objects.get(mail=email)

        self.assertEqual(email.edi_data, str(email_message_dto.attachment[1]))
        self.assertEqual(email.extract_type, ExtractTypeEnum.USAGE_UPDATE)
        self.assertEqual(email.response_filename, None)
        self.assertEqual(email.response_data, None)
        self.assertEqual(email.edi_filename, email_message_dto.attachment[0])
        self.assertEqual(usage_update.hmrc_run_number, self.hmrc_run_number)
        self.assertEqual(usage_update.spire_run_number, email_message_dto.run_number)
        self.assertEqual(email.raw_data, email_message_dto.raw_data)

    def test_bad_mail_data_serialized_successfully(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender="test@example.com",
            receiver="receiver@example.com",
            body="body",
            subject="subject",
            attachment=[],
            raw_data="qwerty",
        )

        initial_issues_count = Mail.objects.invalid().count()
        initial_license_update_count = Mail.objects.valid().count()
        lite_log(
            logger,
            logging.DEBUG,
            f"ini: issue count={initial_issues_count}, license update count {initial_license_update_count}",
        )
        serialize_email_message(email_message_dto)

        self.assertEqual(Mail.objects.invalid().count(), initial_issues_count + 1)
        self.assertEqual(Mail.objects.valid().count(), initial_license_update_count)

        email = Mail.objects.invalid().last()

        self.assertEqual(email.edi_data, "")
        self.assertEqual(email.extract_type, None)
        self.assertEqual(email.response_filename, None)
        self.assertEqual(email.response_data, None)
        self.assertEqual(email.edi_filename, "")
        self.assertEqual(email.raw_data, email_message_dto.raw_data)

    def test_successful_email_db_record_converted_to_dto(self):
        self.mail.status = ReceptionStatusEnum.PENDING

        dto = to_email_message_dto_from(self.mail)

        self.assertEqual(dto.run_number, self.usage_update.spire_run_number)
        self.assertEqual(dto.sender, HMRC_ADDRESS)
        self.assertEqual(dto.attachment[0], self.mail.edi_filename)
        self.assertEqual(dto.attachment[1], self.mail.edi_data)
        self.assertEqual(dto.subject, self.mail.edi_filename)
        self.assertEqual(dto.receiver, SPIRE_ADDRESS)
        self.assertEqual(dto.body, None)
        self.assertEqual(dto.raw_data, None)

    def test_licence_update_reply_is_saved(self):
        self.mail.extract_type = ExtractTypeEnum.LICENCE_UPDATE
        self.mail.status = ReceptionStatusEnum.REPLY_PENDING
        self.mail.save()

        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=HMRC_ADDRESS,
            receiver=SPIRE_ADDRESS,
            body="body",
            subject=self.licence_update_reply_name,
            attachment=[
                self.licence_update_reply_name,
                self.licence_update_reply_body,
            ],
            raw_data="qwerty",
        )

        serialize_email_message(email_message_dto)
        self.mail.refresh_from_db()
        logger.debug("resp data: {}".format(self.mail.response_data))
        self.assertIn(
            self.mail.response_data, self.licence_update_reply_body,
        )
        self.assertEqual(self.mail.status, ReceptionStatusEnum.REPLY_RECEIVED)
        self.assertIsNotNone(self.mail.response_date)

    def test_usage_update_reply_is_saved(self):
        self.mail.status = ReceptionStatusEnum.REPLY_PENDING
        self.mail.save()
        print_all_mails()
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=SPIRE_ADDRESS,
            receiver=HMRC_ADDRESS,
            body="body",
            subject=self.usage_update_reply_name,
            attachment=[self.usage_update_reply_name, self.usage_update_reply_body,],
            raw_data="qwerty",
        )

        serialize_email_message(email_message_dto)
        self.mail.refresh_from_db()

        self.assertEqual(self.mail.status, ReceptionStatusEnum.REPLY_RECEIVED)
        self.assertIsNotNone(self.mail.response_date)

        self.assertIn(
            self.mail.response_data, self.usage_update_reply_body,
        )

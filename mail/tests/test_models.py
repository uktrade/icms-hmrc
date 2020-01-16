from conf.test_client import LiteHMRCTestClient
from mail.dtos import EmailMessageDto
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.models import Mail, LicenceUpdate
from mail.services.data_processing import (
    process_and_save_email_message,
    collect_and_send_data_to_dto,
)
from mail.services.helpers import convert_source_to_sender


class TestModels(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

        self.hmrc_run_number = 28
        self.source_run_number = 15
        self.mail = Mail.objects.create(
            edi_data="blank",
            extract_type=ExtractTypeEnum.INSERT,
            status=ReceptionStatusEnum.ACCEPTED,
            edi_filename="blank",
        )

        self.licence_update = LicenceUpdate.objects.create(
            mail=self.mail,
            hmrc_run_number=self.hmrc_run_number,
            source_run_number=self.source_run_number,
            source=SourceEnum.SPIRE,
        )

    def test_email_processed_successfully(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender="test@spire.com",
            receiver="receiver@example.com",
            body="body",
            subject="subject",
            attachment=["filename", "a line".encode("ascii", "replace")],
            raw_data="qwerty",
        )

        process_and_save_email_message(email_message_dto)

        email = Mail.objects.valid().last()
        licence_update = LicenceUpdate.objects.get(mail=email)

        self.assertEqual(
            email.edi_data, email_message_dto.attachment[1].decode("ascii", "replace")
        )
        self.assertEqual(email.extract_type, ExtractTypeEnum.INSERT)
        self.assertEqual(email.response_file, None)
        self.assertEqual(email.response_date, None)
        self.assertEqual(email.edi_filename, email_message_dto.attachment[0])
        self.assertEqual(licence_update.source_run_number, email_message_dto.run_number)
        self.assertEqual(licence_update.hmrc_run_number, self.hmrc_run_number + 1)
        self.assertEqual(email.raw_data, email_message_dto.raw_data)

    def test_bad_email_sent_to_issues_log(self):
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

        process_and_save_email_message(email_message_dto)

        self.assertEqual(Mail.objects.invalid().count(), initial_issues_count + 1)
        self.assertEqual(Mail.objects.valid().count(), initial_license_update_count)

        email = Mail.objects.invalid().last()

        self.assertEqual(email.edi_data, "")
        self.assertEqual(email.extract_type, ExtractTypeEnum.INSERT)
        self.assertEqual(email.response_file, None)
        self.assertEqual(email.response_date, None)
        self.assertEqual(email.edi_filename, "")
        self.assertEqual(email.raw_data, email_message_dto.raw_data)

    def test_successful_email_db_record_converted_to_dto(self):
        dto = collect_and_send_data_to_dto(self.mail)

        self.assertEqual(dto.run_number, self.licence_update.hmrc_run_number)
        self.assertEqual(
            dto.sender, convert_source_to_sender(self.licence_update.source)
        )
        self.assertEqual(dto.attachment[0], self.mail.edi_filename)
        self.assertEqual(
            dto.attachment[1], self.mail.edi_data.encode("ascii", "replace")
        )
        self.assertEqual(dto.subject, "some_subject")
        self.assertEqual(dto.receiver, "HMRC")
        self.assertEqual(dto.body, "")
        self.assertEqual(dto.raw_data, None)

import logging
from datetime import datetime
from django.db import IntegrityError

from django.conf import settings
from rest_framework.exceptions import ValidationError

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.builders import build_sent_filename, build_sent_file_data
from mail.libraries.data_processors import (
    serialize_email_message,
    to_email_message_dto_from,
)
from mail.libraries.email_message_dto import EmailMessageDto
from mail.models import Mail, LicenceData, UsageData
from mail.tests.libraries.client import LiteHMRCTestClient


class TestDataProcessors(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

        self.hmrc_run_number = 28
        self.source_run_number = 15
        self.mail = Mail.objects.create(
            edi_data=self.licence_data_file_body.decode("utf-8"),
            extract_type=ExtractTypeEnum.USAGE_DATA,
            status=ReceptionStatusEnum.REPLY_SENT,
            edi_filename=self.licence_data_reply_name,
        )

        self.licence_data = LicenceData.objects.create(
            mail=self.mail,
            hmrc_run_number=self.hmrc_run_number,
            source_run_number=self.source_run_number,
            source=SourceEnum.SPIRE,
        )

        self.usage_data = UsageData.objects.create(
            mail=self.mail,
            spire_run_number=self.source_run_number,
            hmrc_run_number=self.hmrc_run_number,
        )

    def test_mail_create_fails_with_empty_edi_values(self):
        with self.assertRaises(IntegrityError):
            Mail.objects.create()

    def test_mail_data_serialized_successfully(self):
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.SPIRE_ADDRESS,
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="body",
            subject=self.licence_usage_file_name,
            attachment=[self.licence_usage_file_name, self.licence_usage_file_body],
            raw_data="",
        )
        self.assertRaises(ValidationError, serialize_email_message, email_message_dto)

        email = Mail.objects.last()
        usage_data = UsageData.objects.get(mail=email)

        self.assertEqual(email.extract_type, ExtractTypeEnum.USAGE_DATA)
        self.assertEqual(email.response_filename, None)
        self.assertEqual(email.response_data, None)
        self.assertEqual(usage_data.hmrc_run_number, self.hmrc_run_number)
        self.assertEqual(usage_data.spire_run_number, email_message_dto.run_number)
        self.assertEqual(email.raw_data, email_message_dto.raw_data)

    def test_successful_email_db_record_converted_to_dto(self):
        self.mail.status = ReceptionStatusEnum.PENDING

        dto = to_email_message_dto_from(self.mail)

        self.assertEqual(dto.run_number, self.usage_data.spire_run_number)
        self.assertEqual(dto.sender, settings.HMRC_ADDRESS)
        self.assertEqual("ILBDOTI_live_CHIEF_licenceReply_49543_201902080025", self.mail.edi_filename)
        self.assertEqual("ILBDOTI_live_CHIEF_licenceReply_49543_201902080025", self.mail.edi_filename)
        self.assertEqual(dto.receiver, settings.SPIRE_ADDRESS)
        self.assertTrue(isinstance(dto.date, datetime))
        self.assertEqual(dto.body, None)
        self.assertEqual(dto.raw_data, None)

    def test_licence_data_reply_is_saved(self):
        self.mail.extract_type = ExtractTypeEnum.LICENCE_DATA
        self.mail.status = ReceptionStatusEnum.REPLY_PENDING
        self.mail.save()

        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.SPIRE_ADDRESS,
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="body",
            subject=self.licence_data_reply_name,
            attachment=[
                self.licence_data_reply_name,
                self.licence_data_reply_body,
            ],
            raw_data="qwerty",
        )

        serialize_email_message(email_message_dto)
        self.mail.refresh_from_db()
        logging.debug("resp data: {}".format(self.mail.response_data))
        self.assertEqual(self.mail.status, ReceptionStatusEnum.REPLY_RECEIVED)
        self.assertIsNotNone(self.mail.response_date)

    def test_usage_data_reply_is_saved(self):
        self.mail.status = ReceptionStatusEnum.REPLY_PENDING
        self.mail.save()
        email_message_dto = EmailMessageDto(
            run_number=self.source_run_number + 1,
            sender=settings.SPIRE_ADDRESS,
            receiver=settings.HMRC_ADDRESS,
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="body",
            subject=self.usage_data_reply_name,
            attachment=[self.usage_data_reply_name, self.usage_data_reply_body],
            raw_data="qwerty",
        )

        serialize_email_message(email_message_dto)
        self.mail.refresh_from_db()

        self.assertEqual(self.mail.status, ReceptionStatusEnum.REPLY_RECEIVED)
        self.assertIsNotNone(self.mail.response_date)

        self.assertIn(
            self.mail.response_data,
            self.usage_data_reply_body.decode("utf-8"),
        )

    def test_licence_reply_does_not_throw_exception_if_mail_already_updated(self):
        self.mail.extract_type = ExtractTypeEnum.LICENCE_DATA
        self.mail.status = ReceptionStatusEnum.REPLY_SENT
        self.mail.save()

        response_date = self.mail.response_date

        email_message_dto = EmailMessageDto(
            run_number=self.hmrc_run_number,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.EMAIL_USER,
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="body",
            subject=self.licence_data_reply_name,
            attachment=[self.licence_data_reply_name, self.licence_data_reply_body],
            raw_data="qwerty",
        )

        serialize_email_message(email_message_dto)

        self.mail.refresh_from_db()

        self.assertEqual(response_date, self.mail.response_date)

    def test_build_sent_filename(self):
        run_number = 4321
        filename = "abc_xyz_nnn_yyy_<runnumber>_datetime"

        self.assertEqual(build_sent_filename(filename, run_number), f"abc_xyz_nnn_yyy_{run_number}_datetime")

    def test_build_sent_file_data(self):
        run_number = 4321
        file_data = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\{:04d}{:02d}{:02d}{:02d}{:02d}\\1234"
            + "\n2\\licence\\1234\\insert\\GBSIEL/2020/0000001/P\\siel\\E\\1234\\1234"
            + "\n3\\trader\\0192301\\123791\\20200602\\20220602\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Tennessee\\99580"
        )
        expected_file_data = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\{:04d}{:02d}{:02d}{:02d}{:02d}\\4321"
            + "\n2\\licence\\1234\\insert\\GBSIEL/2020/0000001/P\\siel\\E\\1234\\1234"
            + "\n3\\trader\\0192301\\123791\\20200602\\20220602\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Tennessee\\99580"
        )
        self.assertEqual(build_sent_file_data(file_data, run_number), expected_file_data)

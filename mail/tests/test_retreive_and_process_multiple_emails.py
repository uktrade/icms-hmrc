from django.conf import settings

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.data_processors import serialize_email_message
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import select_email_for_sending
from mail.models import Mail, LicenceData
from mail.tests.libraries.client import LiteHMRCTestClient


class MultipleEmailRetrievalTests(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()
        self.dto_1 = EmailMessageDto(
            run_number=49543,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.EMAIL_USER,
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="lite licence reply",
            subject="ILBDOTI_live_CHIEF_licenceReply_49543_201901130300",
            attachment=[
                "ILBDOTI_live_CHIEF_licenceReply_49543_201901130300",
                self.licence_data_reply_body,
            ],
            raw_data="qwerty",
        )
        self.dto_2 = EmailMessageDto(
            run_number=17,
            sender=settings.SPIRE_ADDRESS,
            receiver=settings.EMAIL_USER,
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="spire licence update",
            subject="ILBDOTI_live_CHIEF_licenceData_17_201901130300",
            attachment=[
                "ILBDOTI_live_CHIEF_licenceData_49543_201901130300",
                self.licence_data_file_body,
            ],
            raw_data="qwerty",
        )
        self.dto_3 = EmailMessageDto(
            run_number=49542,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.EMAIL_USER,
            date="Mon, 17 May 2021 14:20:18 +0100",
            body="spire licence reply",
            subject="ILBDOTI_live_CHIEF_licenceReply_49542_201901130300",
            attachment=["ILBDOTI_live_CHIEF_licenceReply_49542_201901130300", self.licence_data_reply_body],
            raw_data="qwerty",
        )

    def test_duplicate_emails_and_licence_datas_not_saved(self):
        mail = Mail.objects.create(
            edi_filename=self.dto_2.attachment[0],
            edi_data=self.dto_2.attachment[1],
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            status=ReceptionStatusEnum.REPLY_SENT,
        )
        LicenceData.objects.create(source_run_number=17, hmrc_run_number=49542, mail=mail, source=SourceEnum.SPIRE)
        mail_count = Mail.objects.count()
        licence_data_count = LicenceData.objects.count()

        serialize_email_message(self.dto_3)

        self.assertEqual(mail_count, Mail.objects.count())
        self.assertEqual(licence_data_count, LicenceData.objects.count())

    def test_emails_are_sequenced_correctly(self):
        mail = Mail.objects.create(
            edi_filename="something",
            edi_data="some data",
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            status=ReceptionStatusEnum.REPLY_PENDING,
        )
        LicenceData.objects.create(source_run_number=4, hmrc_run_number=49543, mail=mail, source=SourceEnum.LITE)

        mail_lite = serialize_email_message(self.dto_2)
        mail_spire = serialize_email_message(self.dto_1)

        self.assertEqual(Mail.objects.filter(status=ReceptionStatusEnum.REPLY_RECEIVED).count(), 1)
        self.assertEqual(Mail.objects.filter(status=ReceptionStatusEnum.PENDING).count(), 1)

        mail = select_email_for_sending()

        self.assertEqual(mail_spire, mail)

        mail_spire.status = ReceptionStatusEnum.REPLY_SENT
        mail_spire.save()

        mail = select_email_for_sending()

        self.assertEqual(mail_lite, mail)

    def test_retry(self):
        serialize_email_message(self.dto_2)
        mail_count = Mail.objects.count()
        licence_data_count = LicenceData.objects.count()
        mail = serialize_email_message(self.dto_2)
        mail.response_data = "rejected"
        mail.save()

        serialize_email_message(self.dto_2)

        self.assertEqual(Mail.objects.count(), mail_count + 1)
        self.assertEqual(LicenceData.objects.count(), licence_data_count + 1)

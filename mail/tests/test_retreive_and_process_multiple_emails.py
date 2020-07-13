from django.test import tag

from conf.settings import HMRC_ADDRESS, SPIRE_ADDRESS, EMAIL_USER
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.data_processors import serialize_email_message
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import select_email_for_sending
from mail.models import Mail, LicenceUpdate
from mail.tests.libraries.client import LiteHMRCTestClient


class MultipleEmailRetrievalTests(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()
        self.dto_1 = EmailMessageDto(
            run_number=49543,
            sender=HMRC_ADDRESS,
            receiver=EMAIL_USER,
            body="lite licence reply",
            subject="ILBDOTI_live_CHIEF_licenceReply_49543_201901130300",
            attachment=["ILBDOTI_live_CHIEF_licenceReply_49543_201901130300", self.licence_update_reply_body,],
            raw_data="qwerty",
        )
        self.dto_2 = EmailMessageDto(
            run_number=17,
            sender=SPIRE_ADDRESS,
            receiver=EMAIL_USER,
            body="spire licence update",
            subject="ILBDOTI_live_CHIEF_licenceUpdate_17_201901130300",
            attachment=["ILBDOTI_live_CHIEF_licenceUpdate_49543_201901130300", self.licence_update_file_body,],
            raw_data="qwerty",
        )
        self.dto_3 = EmailMessageDto(
            run_number=49542,
            sender=HMRC_ADDRESS,
            receiver=EMAIL_USER,
            body="spire licence reply",
            subject="ILBDOTI_live_CHIEF_licenceReply_49542_201901130300",
            attachment=["ILBDOTI_live_CHIEF_licenceReply_49542_201901130300", self.licence_update_reply_body],
            raw_data="qwerty",
        )

    @tag("no-duplication")
    def test_duplicate_emails_and_licence_updates_not_saved(self):
        mail = Mail.objects.create(
            edi_filename=self.dto_2.attachment[0],
            edi_data=self.dto_2.attachment[1],
            extract_type=ExtractTypeEnum.LICENCE_UPDATE,
            status=ReceptionStatusEnum.REPLY_SENT,
        )
        LicenceUpdate.objects.create(source_run_number=17, hmrc_run_number=49542, mail=mail, source=SourceEnum.SPIRE)
        mail_count = Mail.objects.count()
        licence_update_count = LicenceUpdate.objects.count()

        serialize_email_message(self.dto_3)

        self.assertEqual(mail_count, Mail.objects.count())
        self.assertEqual(licence_update_count, LicenceUpdate.objects.count())

    @tag("sequencing")
    def test_emails_are_sequenced_correctly(self):
        mail = Mail.objects.create(
            edi_filename="something",
            edi_data="some data",
            extract_type=ExtractTypeEnum.LICENCE_UPDATE,
            status=ReceptionStatusEnum.REPLY_PENDING,
        )
        LicenceUpdate.objects.create(source_run_number=4, hmrc_run_number=49543, mail=mail, source=SourceEnum.LITE)

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

    @tag("retry")
    def test_retry(self):
        serialize_email_message(self.dto_2)
        mail_count = Mail.objects.count()
        licence_update_count = LicenceUpdate.objects.count()
        mail = serialize_email_message(self.dto_2)
        mail.response_data = "rejected"
        mail.save()

        serialize_email_message(self.dto_2)

        self.assertEqual(Mail.objects.count(), mail_count + 1)
        self.assertEqual(LicenceUpdate.objects.count(), licence_update_count + 1)

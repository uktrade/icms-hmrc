from django.test import tag

from mail.enums import ReceptionStatusEnum, ExtractTypeEnum
from mail.libraries.helpers import select_email_for_sending
from mail.models import Mail, UsageData
from mail.tests.libraries.client import LiteHMRCTestClient


class EmailSelectTests(LiteHMRCTestClient):
    @tag("select-email")
    def test_select_first_email_which_is_reply_received(self):
        mail_0 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_SENT)
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_RECEIVED)
        mail_2 = Mail.objects.create(status=ReceptionStatusEnum.PENDING)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    @tag("select-email")
    def test_select_earliest_email_with_reply_received(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_RECEIVED)
        mail_2 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_RECEIVED)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    @tag("select-email")
    def test_select_reply_received_when_earlier_email_has_pending(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.PENDING)
        mail_2 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_RECEIVED)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_2)

    @tag("select-email")
    def test_select_pending_when_later_email_has_reply_sent(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.PENDING)
        mail_2 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_SENT)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    @tag("select-email")
    def test_do_not_select_email_if_email_in_flight(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.PENDING)
        mail_2 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_PENDING)

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    @tag("select-email")
    def test_do_not_select_if_no_emails_pending_or_reply_received(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_PENDING)
        mail_2 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_SENT)

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    @tag("select-email")
    def test_do_not_select_usage_reply_if_spire_response_not_received(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_PENDING)
        UsageData.objects.create(
            mail=mail_1, spire_run_number=1, hmrc_run_number=1, lite_response={"reply": "this is a response"}
        )

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    @tag("select-email")
    def test_do_not_select_usage_reply_if_lite_response_not_received(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_RECEIVED, extract_type=ExtractTypeEnum.USAGE_DATA)
        UsageData.objects.create(mail=mail_1, spire_run_number=1, hmrc_run_number=1, has_lite_data=True)

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    @tag("select-email")
    def test_email_selected_if_no_lite_data(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_RECEIVED, extract_type=ExtractTypeEnum.USAGE_DATA)
        UsageData.objects.create(mail=mail_1, spire_run_number=1, hmrc_run_number=1, has_lite_data=False)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    @tag("select-email")
    def test_email_selected_if_no_spire_data(self):
        mail_1 = Mail.objects.create(status=ReceptionStatusEnum.REPLY_RECEIVED, extract_type=ExtractTypeEnum.USAGE_DATA)
        UsageData.objects.create(
            mail=mail_1,
            spire_run_number=1,
            hmrc_run_number=1,
            has_lite_data=True,
            lite_response={"reply": "1"},
            lite_sent_at="2020-11-11",
        )

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

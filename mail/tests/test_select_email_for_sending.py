from django.test import tag

from mail.enums import ReceptionStatusEnum
from mail.libraries.helpers import select_email_for_sending
from mail.models import Mail
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

from datetime import datetime, timezone
from unittest import mock

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.helpers import select_email_for_sending
from mail.libraries.routing_controller import check_and_route_emails
from mail.models import LicenceData, Mail, UsageData
from mail.tests.libraries.client import LiteHMRCTestClient


class EmailSelectTests(LiteHMRCTestClient):
    def get_mail(self, **values):
        return Mail.objects.create(edi_filename="filename", edi_data="1\\fileHeader\\CHIEF\\SPIRE\\", **values)

    def test_select_first_email_which_is_reply_received(self):
        mail_0 = self.get_mail(status=ReceptionStatusEnum.REPLY_SENT)
        mail_1 = self.get_mail(status=ReceptionStatusEnum.REPLY_RECEIVED)
        mail_2 = self.get_mail(status=ReceptionStatusEnum.PENDING)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    def test_select_earliest_email_with_reply_received(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.REPLY_RECEIVED)
        mail_2 = self.get_mail(status=ReceptionStatusEnum.REPLY_RECEIVED)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    def test_select_reply_received_when_earlier_email_has_pending(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.PENDING)
        mail_2 = self.get_mail(status=ReceptionStatusEnum.REPLY_RECEIVED)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_2)

    def test_select_pending_when_later_email_has_reply_sent(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.PENDING)
        mail_2 = self.get_mail(status=ReceptionStatusEnum.REPLY_SENT)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    def test_do_not_select_email_if_email_in_flight(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.PENDING)
        mail_2 = self.get_mail(status=ReceptionStatusEnum.REPLY_PENDING)

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    def test_do_not_select_if_no_emails_pending_or_reply_received(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.REPLY_PENDING)
        mail_2 = self.get_mail(status=ReceptionStatusEnum.REPLY_SENT)

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    def test_do_not_select_usage_reply_if_spire_response_not_received(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.REPLY_PENDING)
        UsageData.objects.create(
            mail=mail_1, spire_run_number=1, hmrc_run_number=1, lite_response={"reply": "this is a response"}
        )

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    def test_do_not_select_usage_reply_if_lite_response_not_received(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.REPLY_RECEIVED, extract_type=ExtractTypeEnum.USAGE_DATA)
        UsageData.objects.create(mail=mail_1, spire_run_number=1, hmrc_run_number=1, has_lite_data=True)

        mail = select_email_for_sending()

        self.assertEqual(mail, None)

    def test_email_selected_if_no_lite_data(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.REPLY_RECEIVED, extract_type=ExtractTypeEnum.USAGE_DATA)
        UsageData.objects.create(mail=mail_1, spire_run_number=1, hmrc_run_number=1, has_lite_data=False)

        mail = select_email_for_sending()

        self.assertEqual(mail, mail_1)

    def test_email_selected_if_no_spire_data(self):
        mail_1 = self.get_mail(status=ReceptionStatusEnum.REPLY_RECEIVED, extract_type=ExtractTypeEnum.USAGE_DATA)
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

    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller._get_email_message_dtos")
    def test_case1_sending_of_pending_licencedata_mails(self, email_dtos, send_mail):
        """
        Ensure pending mails are sent and status updated as expected.

        Case1: When only one licenceData mail is pending

        | Mail id      | edi_filename                                    | status         |
        + -------------+-------------------------------------------------+----------------+
        | ac1323b135fb | CHIEF_LIVE_SPIRE_licenceData_98720_202106180855 | reply_sent     |
        | d2d9b8d1f582 | CHIEF_LIVE_SPIRE_licenceData_98721_202106180855 | reply_sent     |
        | dc1323b1abcd | CHIEF_LIVE_SPIRE_licenceData_98722_202106180855 | pending        |
        """
        num_sent_mails = 3
        start_run_number = 78120
        email_dtos.return_value = []
        send_mail.wraps = lambda x: x
        for i in range(num_sent_mails):
            mail = self.get_mail(extract_type=ExtractTypeEnum.LICENCE_DATA, status=ReceptionStatusEnum.REPLY_SENT)
            LicenceData.objects.create(
                mail=mail,
                source_run_number=start_run_number + i,
                hmrc_run_number=start_run_number + i,
                source=SourceEnum.SPIRE,
                licence_ids=f"{i}",
            )

        next_run_number = start_run_number + num_sent_mails
        filename = self.licence_data_file_name
        mail_body = self.licence_data_file_body.decode("utf-8")
        pending_mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.PENDING,
            sent_at=datetime.now(timezone.utc),
        )
        LicenceData.objects.create(
            mail=pending_mail,
            source_run_number=next_run_number,
            hmrc_run_number=next_run_number,
            source=SourceEnum.SPIRE,
            licence_ids=f"{next_run_number}",
        )
        check_and_route_emails()

        # assert that the pending mail is sent and status updated
        mail = Mail.objects.get(id=pending_mail.id)
        send_mail.assert_called_once()
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_PENDING)

    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller._get_email_message_dtos")
    def test_case2_sending_of_pending_usagedata_mails(self, email_dtos, send_mail):
        """
        Case2: When only usageData mails are pending. Multiple mails are possible if none
        are received over the weekend and both arrived on monday.

        | Mail id      | edi_filename                                    | status         |
        + -------------+-------------------------------------------------+----------------+
        | ac1323b135fb | CHIEF_LIVE_SPIRE_licenceData_98720_202106180855 | reply_sent     |
        | d2d9b8d1f582 | CHIEF_LIVE_SPIRE_licenceData_98721_202106180855 | reply_sent     |
        | dc1323b1abcd | CHIEF_LIVE_SPIRE_usageData_5050_202106180855    | pending        |
        | bb2223b132bc | CHIEF_LIVE_SPIRE_usageData_5051_202106180855    | pending        |
        """
        filename_template = "CHIEF_LIVE_CHIEF_usageData_{run_number}_202104070888"
        num_sent_mails = 3
        start_run_number = 78120
        email_dtos.return_value = []
        send_mail.wraps = lambda x: x
        for i in range(num_sent_mails):
            mail = self.get_mail(extract_type=ExtractTypeEnum.LICENCE_DATA, status=ReceptionStatusEnum.REPLY_SENT)
            LicenceData.objects.create(
                mail=mail,
                source_run_number=start_run_number + i,
                hmrc_run_number=start_run_number + i,
                source=SourceEnum.SPIRE,
                licence_ids=f"{i}",
            )
        usage_run_number = 5050
        pending_mails = []
        for i in range(2):
            usage_run_number = usage_run_number + i
            filename = filename_template.format(run_number=usage_run_number)
            mail_body = self.licence_usage_file_body.decode("utf-8")
            mail = Mail.objects.create(
                extract_type=ExtractTypeEnum.USAGE_DATA,
                edi_filename=filename,
                edi_data=mail_body,
                status=ReceptionStatusEnum.PENDING,
            )
            UsageData.objects.create(
                mail=mail,
                spire_run_number=usage_run_number,
                hmrc_run_number=usage_run_number,
                licence_ids=f"{usage_run_number}",
            )
            pending_mails.append(mail)

        for i in range(2):
            check_and_route_emails()

            # assert that the pending mail is sent and status updated
            mail = Mail.objects.get(id=pending_mails[i].id)
            send_mail.assert_called()
            self.assertEqual(send_mail.call_count, int(i + 1))
            self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_SENT)

    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller._get_email_message_dtos")
    def test_case3_sending_of_pending_licencedata_and_usagedata_mails_1(self, email_dtos, send_mail):
        """
        Case3.1: When both licenceData and usageData mails are pending. This is possible if
        we haven't received any usageData files over the weekend and on monday they have
        arrived at the same time of a new licenceData file. This is unlikely but possible.

        | Mail id      | edi_filename                                    | status         |
        + -------------+-------------------------------------------------+----------------+
        | ac1323b135fb | CHIEF_LIVE_SPIRE_licenceData_98720_202106180855 | reply_sent     |
        | d2d9b8d1f582 | CHIEF_LIVE_SPIRE_licenceData_98721_202106180855 | reply_sent     |
        | dc1323b1abcd | CHIEF_LIVE_SPIRE_usageData_5050_202106180855    | pending        |
        | bb2223b132bc | CHIEF_LIVE_SPIRE_usageData_5051_202106180855    | pending        |
        | 541323b18976 | CHIEF_LIVE_SPIRE_licenceData_98722_202106180855 | pending        |
        """
        filename_template = "CHIEF_LIVE_CHIEF_usageData_{run_number}_202104070888"
        num_sent_mails = 3
        start_run_number = 78120
        email_dtos.return_value = []
        send_mail.wraps = lambda x: x
        for i in range(num_sent_mails):
            mail = self.get_mail(extract_type=ExtractTypeEnum.LICENCE_DATA, status=ReceptionStatusEnum.REPLY_SENT)
            LicenceData.objects.create(
                mail=mail,
                source_run_number=start_run_number + i,
                hmrc_run_number=start_run_number + i,
                source=SourceEnum.SPIRE,
                licence_ids=f"{i}",
            )

        usage_run_number = 5050
        pending_mails = []
        for i in range(2):
            usage_run_number = usage_run_number + i
            filename = filename_template.format(run_number=usage_run_number)
            mail_body = self.licence_usage_file_body.decode("utf-8")
            mail = Mail.objects.create(
                extract_type=ExtractTypeEnum.USAGE_DATA,
                edi_filename=filename,
                edi_data=mail_body,
                status=ReceptionStatusEnum.PENDING,
            )
            UsageData.objects.create(
                mail=mail,
                spire_run_number=usage_run_number,
                hmrc_run_number=usage_run_number,
                licence_ids=f"{usage_run_number}",
            )
            pending_mails.append(mail)

        licence_data_run_number = start_run_number + num_sent_mails + 1
        filename = self.licence_data_file_name
        mail_body = self.licence_data_file_body.decode("utf-8")
        mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.PENDING,
        )
        LicenceData.objects.create(
            mail=mail,
            source_run_number=licence_data_run_number,
            hmrc_run_number=licence_data_run_number,
            source=SourceEnum.SPIRE,
            licence_ids=f"{licence_data_run_number}",
        )
        pending_mails.append(mail)

        for i in range(3):
            check_and_route_emails()

            # assert that the pending mail is sent and status updated
            mail = Mail.objects.get(id=pending_mails[i].id)
            send_mail.assert_called()
            self.assertEqual(send_mail.call_count, int(i + 1))

            if mail.extract_type == ExtractTypeEnum.LICENCE_DATA:
                self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_PENDING)
            elif mail.extract_type == ExtractTypeEnum.USAGE_DATA:
                self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_SENT)

    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller._get_email_message_dtos")
    def test_case3_sending_of_pending_licencedata_and_usagedata_mails_2(self, email_dtos, send_mail):
        """
        Another variation of case3 is,

        | Mail id      | edi_filename                                    | status         |
        + -------------+-------------------------------------------------+----------------+
        | ac1323b135fb | CHIEF_LIVE_SPIRE_licenceData_98720_202106180855 | reply_sent     |
        | d2d9b8d1f582 | CHIEF_LIVE_SPIRE_licenceData_98721_202106180855 | reply_sent     |
        | dc1323b1abcd | CHIEF_LIVE_SPIRE_usageData_5050_202106180855    | reply_sent     |
        | 541323b18976 | CHIEF_LIVE_SPIRE_licenceData_98722_202106180855 | pending        |
        """
        num_sent_mails = 3
        start_run_number = 78120
        usage_run_number = 5050
        email_dtos.return_value = []
        send_mail.wraps = lambda x: x
        for i in range(num_sent_mails):
            mail = self.get_mail(extract_type=ExtractTypeEnum.LICENCE_DATA, status=ReceptionStatusEnum.REPLY_SENT)
            LicenceData.objects.create(
                mail=mail,
                source_run_number=start_run_number + i,
                hmrc_run_number=start_run_number + i,
                source=SourceEnum.SPIRE,
                licence_ids=f"{i}",
            )

        filename_template = "CHIEF_LIVE_CHIEF_usageData_{run_number}_202104070888"
        filename = filename_template.format(run_number=usage_run_number)
        mail_body = self.licence_usage_file_body.decode("utf-8")
        mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.USAGE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.REPLY_SENT,
        )
        UsageData.objects.create(
            mail=mail,
            spire_run_number=usage_run_number,
            hmrc_run_number=usage_run_number,
            licence_ids=f"{usage_run_number}",
        )

        licence_data_run_number = start_run_number + num_sent_mails + 1
        filename = self.licence_data_file_name
        mail_body = self.licence_data_file_body.decode("utf-8")
        pending_mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.PENDING,
        )
        LicenceData.objects.create(
            mail=pending_mail,
            source_run_number=licence_data_run_number,
            hmrc_run_number=licence_data_run_number,
            source=SourceEnum.SPIRE,
            licence_ids=f"{licence_data_run_number}",
        )

        check_and_route_emails()

        # assert that the pending mail is sent and status updated
        mail = Mail.objects.get(id=pending_mail.id)
        send_mail.assert_called_once()
        self.assertEqual(mail.status, ReceptionStatusEnum.REPLY_PENDING)

    @mock.patch("mail.libraries.routing_controller.send")
    @mock.patch("mail.libraries.routing_controller._get_email_message_dtos")
    def test_case4_sending_of_pending_licencedata_when_waiting_for_reply(self, email_dtos, send_mail):
        """
        Another variation of case3 is,

        | Mail id      | edi_filename                                    | status         |
        + -------------+-------------------------------------------------+----------------+
        | ac1323b135fb | CHIEF_LIVE_SPIRE_licenceData_98720_202106180855 | reply_sent     |
        | d2d9b8d1f582 | CHIEF_LIVE_SPIRE_licenceData_98721_202106180855 | reply_pending  |
        | dc1323b1abcd | CHIEF_LIVE_SPIRE_usageData_5050_202106180855    | reply_sent     |
        | 541323b18976 | CHIEF_LIVE_SPIRE_licenceData_98721_202106180855 | pending        |
        """
        mails_status = [ReceptionStatusEnum.REPLY_SENT, ReceptionStatusEnum.REPLY_PENDING]
        start_run_number = 78120
        usage_run_number = 5050
        email_dtos.return_value = []
        send_mail.wraps = lambda x: x
        for i, status in enumerate(mails_status):
            mail = self.get_mail(extract_type=ExtractTypeEnum.LICENCE_DATA, status=status)
            LicenceData.objects.create(
                mail=mail,
                source_run_number=start_run_number + i,
                hmrc_run_number=start_run_number + i,
                source=SourceEnum.SPIRE,
                licence_ids=f"{i}",
            )

        filename_template = "CHIEF_LIVE_CHIEF_usageData_{run_number}_202104070888"
        filename = filename_template.format(run_number=usage_run_number)
        mail_body = self.licence_usage_file_body.decode("utf-8")
        mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.USAGE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.REPLY_SENT,
        )
        UsageData.objects.create(
            mail=mail,
            spire_run_number=usage_run_number,
            hmrc_run_number=usage_run_number,
            licence_ids=f"{usage_run_number}",
        )

        licence_data_run_number = start_run_number + len(mails_status)
        filename = self.licence_data_file_name
        mail_body = self.licence_data_file_body.decode("utf-8")
        pending_mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename=filename,
            edi_data=mail_body,
            status=ReceptionStatusEnum.PENDING,
        )
        LicenceData.objects.create(
            mail=pending_mail,
            source_run_number=licence_data_run_number,
            hmrc_run_number=licence_data_run_number,
            source=SourceEnum.SPIRE,
            licence_ids=f"{licence_data_run_number}",
        )

        with self.assertRaises(Exception) as err:
            check_and_route_emails()

        self.assertEqual(str(err.exception), "Received another licenceData mail while waiting for reply")

        # assert that the pending mail is sent and status updated
        mail = Mail.objects.get(id=pending_mail.id)
        send_mail.assert_not_called()
        self.assertEqual(mail.status, ReceptionStatusEnum.PENDING)

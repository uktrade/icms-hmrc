import json
import logging

from django.test import testcases
from django.utils import timezone

from conf import settings
from mail.enums import LicenceActionEnum
from mail.libraries.helpers import read_file
from mail.models import LicencePayload
from mail.tests.libraries import colours


class LiteHMRCTestClient(testcases.TestCase):
    TEST_RUN_NUMBER = "49543"

    @classmethod
    def tearDownClass(cls):
        logging.debug("tearDownClass() is called")
        super().tearDownClass()

    def setUp(self):
        if settings.TIME_TESTS:
            self.tick = timezone.now()

        self.licence_usage_file_name = "ILBDOTI_live_CHIEF_usageData_49543_201901130300"
        self.licence_usage_file_body = read_file("mail/tests/files/license_usage_file", mode="rb")
        self.licence_data_reply_body = (
            b"MVxmaWxlSGVhZGVyXENISUVGXFNQSVJFXGxpY2VuY2VSZXBseVwyMDE5MDIwODAwMjVcMTAxMAo"
            b"yXGFjY2VwdGVkXEdCU0lFTC8yMDIwLzAwMDAwMDEvUAozXGFjY2VwdGVkXEdCU0lFTC8yMDIwLz"
            b"AwMDAwMDEvUAo0XGZpbGVUcmFpbGVyXDJcMFww"
        )
        self.usage_update_reply_body = read_file("mail/tests/files/usage_update_reply_file", mode="rb")
        logging.debug("licence_data_reply_body: \n{}".format(self.licence_data_reply_body))
        self.licence_data_reply_name = "ILBDOTI_live_CHIEF_licenceReply_49543_201902080025"

        self.usage_update_reply_name = "ILBDOTI_live_CHIEF_usageReply_49543_201902080025"

        self.licence_data_file_name = "CHIEF_LIVE_SPIRE_licenceData_49543_201902080025"
        self.licence_data_file_name = "ILBDOTI_live_CHIEF_licenceData_49543_201902080025"

        self.licence_data_file_body = read_file("mail/tests/files/license_update_file", mode="rb")
        self.licence_data_file_body = read_file("mail/tests/files/license_update_file", mode="rb")

        self.licence_payload_json = json.loads(read_file("mail/tests/files/licence_payload_file", encoding="utf-8"))

        self.single_siel_licence_payload = LicencePayload.objects.create(
            lite_id=self.licence_payload_json["licence"]["id"],
            reference=self.licence_payload_json["licence"]["reference"],
            data=self.licence_payload_json["licence"],
            action=LicenceActionEnum.INSERT,
        )

    def tearDown(self):
        """
        Print output time for tests if settings.TIME_TESTS is set to True
        """
        if settings.TIME_TESTS:
            self.tock = timezone.now()

            diff = self.tock - self.tick
            time = round(diff.microseconds / 1000, 2)
            colour = colours.green
            emoji = ""

            if time > 100:
                colour = colours.orange
            if time > 300:
                colour = colours.red
                emoji = " 🔥"

            print(self._testMethodName + emoji + " " + colour(str(time) + "ms") + emoji)

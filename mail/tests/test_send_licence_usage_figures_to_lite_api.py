from unittest import mock

from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_207_MULTI_STATUS, HTTP_208_ALREADY_REPORTED

from conf.settings import LITE_API_URL, HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS, LITE_API_REQUEST_TIMEOUT, MAX_ATTEMPTS
from mail.models import Mail, UsageData, LicencePayload
from mail.tasks import send_licence_usage_figures_to_lite_api, schedule_max_tried_task_as_new_task
from mail.tests.libraries.client import LiteHMRCTestClient


class MockTask:
    def __init__(self, attempts: int = 0, exists: bool = True):
        self.attempts = attempts
        self._exists = exists

    def exists(self):
        return self._exists


class MockResponse:
    def __init__(self, json: dict = None, status_code: int = HTTP_207_MULTI_STATUS):
        self.json_data = json or {}
        self.text = str(self.json_data)
        self.status_code = status_code

    def json(self):
        return self.json_data


@mock.patch("mail.apps.BACKGROUND_TASK_ENABLED", False)  # Disable task from being run on app initialization
class UpdateUsagesTaskTests(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()
        self.licence_payload_1 = LicencePayload.objects.create(
            lite_id="2e6f3fe2-40a2-4c7c-8b71-3f0e53f92298", reference="GBSIEL/2020/0000008/P"
        )
        self.licence_payload_2 = LicencePayload.objects.create(
            lite_id="80a3d9b2-09a9-4e86-840f-236d186e5b0c", reference="GBSIEL/2020/0000009/P"
        )
        self.mail = Mail.objects.create(
            edi_data=(
                "1\\fileHeader\\CHIEF\\SPIRE\\usageData\\201901130300\\49543\\\n"
                "2\\licenceUsage\\LU04148/00001\\insert\\GBSIEL/2020/0000008/P\\O\\\n"
                "3\\line\\1\\0\\0\\\n"
                "4\\usage\\O\\9GB000001328000-PE112345\\R\\20190112\\0\\0\\\\000262\\\\\\\\\n"
                "5\\end\\line\\5\n"
                "6\\end\\licenceUsage\\5\n"
                "7\\licenceUsage\\LU04148/00002\\insert\\GBSIEL/2020/0000009/P\\O\\\n"
                "8\\line\\1\\0\\0\\\n"
                "9\\usage\\O\\9GB000003133000-445251012345\\Z\\20190112\\0\\0\\\\000962\\\\\\\\\n"
                "10\\end\\line\\3\n"
                "11\\end\\licenceUsage\\5\n"
                "12\\fileTrailer\\2"
            )
        )
        self.usage_data = UsageData.objects.create(
            id="1e5a4fd0-e581-4efd-9770-ac68e04852d2",
            mail=self.mail,
            licence_ids='["GBSIEL/2020/0000008/P", "GBSIEL/2020/0000009/P"]',
            hmrc_run_number=0,
            spire_run_number=0,
        )

    @mock.patch("mail.tasks.put")
    def test_schedule_usages_for_lite_api_207_ok(self, put_request):
        put_request.return_value = MockResponse(
            json={
                "usage_data_id": "1e5a4fd0-e581-4efd-9770-ac68e04852d2",
                "licences": {
                    "accepted": [
                        {
                            "id": "2e6f3fe2-40a2-4c7c-8b71-3f0e53f92298",
                            "goods": [{"id": "27ac9316-abd0-4dc1-981e-b50714c7fb8c", "usage": 10}],
                        }
                    ],
                    "rejected": [
                        {
                            "id": "80a3d9b2-09a9-4e86-840f-236d186e5b0c",
                            "goods": {
                                "accepted": [{"id": "7aaccfa6-1d60-4a87-9897-3c04c20192e7", "usage": 10}],
                                "rejected": [
                                    {
                                        "id": "87151418-dfff-4688-ab0c-ff8990db5365",
                                        "usage": 10,
                                        "errors": {"id": ["Good not found on Licence."]},
                                    }
                                ],
                            },
                            "errors": {"goods": ["One or more Goods were rejected."]},
                        }
                    ],
                },
            },
            status_code=HTTP_207_MULTI_STATUS,
        )

        send_licence_usage_figures_to_lite_api.now(str(self.usage_data.id))

        self.usage_data.refresh_from_db()
        put_request.assert_called_with(
            f"{LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=LITE_API_REQUEST_TIMEOUT,
        )
        self.usage_data.refresh_from_db()
        self.assertIsNotNone(self.usage_data.lite_sent_at)
        self.assertEqual(self.usage_data.lite_accepted_licences, ["GBSIEL/2020/0000008/P"])
        self.assertEqual(self.usage_data.lite_rejected_licences, ["GBSIEL/2020/0000009/P"])

    @mock.patch("mail.tasks.put")
    def test_schedule_usages_for_lite_api_208_ok(self, put_request):
        original_sent_at = self.usage_data.lite_sent_at
        original_accepted_licences = self.usage_data.lite_accepted_licences
        original_rejected_licences = self.usage_data.lite_rejected_licences
        put_request.return_value = MockResponse(status_code=HTTP_208_ALREADY_REPORTED)

        send_licence_usage_figures_to_lite_api.now(str(self.usage_data.id))

        self.usage_data.refresh_from_db()
        put_request.assert_called_with(
            f"{LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=LITE_API_REQUEST_TIMEOUT,
        )
        self.usage_data.refresh_from_db()
        self.assertEqual(self.usage_data.lite_sent_at, original_sent_at)
        self.assertEqual(self.usage_data.lite_accepted_licences, original_accepted_licences)
        self.assertEqual(self.usage_data.lite_rejected_licences, original_rejected_licences)

    @mock.patch("mail.tasks.put")
    def test_schedule_usages_for_lite_api_400_bad_request(self, put_request):
        put_request.return_value = MockResponse(status_code=HTTP_400_BAD_REQUEST)

        with self.assertRaises(Exception) as error:
            send_licence_usage_figures_to_lite_api.now(str(self.usage_data.id))

        self.usage_data.refresh_from_db()
        put_request.assert_called_with(
            f"{LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=LITE_API_REQUEST_TIMEOUT,
        )
        self.usage_data.refresh_from_db()
        self.assertIsNone(self.usage_data.lite_sent_at)

    @mock.patch("mail.tasks.schedule_max_tried_task_as_new_task")
    @mock.patch("mail.tasks.Task.objects.get")
    @mock.patch("mail.tasks.put")
    def test_schedule_usages_for_lite_api_max_tried_task(self, put_request, get_task, schedule_new_task):
        put_request.return_value = MockResponse(status_code=HTTP_400_BAD_REQUEST)
        get_task.return_value = MockTask(MAX_ATTEMPTS - 1)
        schedule_new_task.return_value = None

        with self.assertRaises(Exception) as error:
            send_licence_usage_figures_to_lite_api.now(str(self.usage_data.id))

        self.usage_data.refresh_from_db()
        put_request.assert_called_with(
            f"{LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=LITE_API_REQUEST_TIMEOUT,
        )
        schedule_new_task.assert_called_with(str(self.usage_data.id))
        self.usage_data.refresh_from_db()
        self.assertIsNone(self.usage_data.lite_sent_at)

    @mock.patch("mail.tasks.send_licence_usage_figures_to_lite_api")
    def test_schedule_new_task(self, send_licence_usage_figures):
        send_licence_usage_figures.return_value = None

        schedule_max_tried_task_as_new_task(str(self.usage_data.id))

        send_licence_usage_figures.assert_called_with(str(self.usage_data.id), schedule=mock.ANY)

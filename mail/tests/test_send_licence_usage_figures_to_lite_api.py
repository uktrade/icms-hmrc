from unittest import mock
from uuid import uuid4

from django.conf import settings
from django.test import override_settings
from rest_framework.status import HTTP_207_MULTI_STATUS, HTTP_208_ALREADY_REPORTED, HTTP_400_BAD_REQUEST

from mail.models import GoodIdMapping, LicenceIdMapping, LicencePayload, Mail, UsageData
from mail.tasks import schedule_max_tried_task_as_new_task, send_licence_usage_figures_to_lite_api
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


@override_settings(BACKGROUND_TASK_ENABLED=False)  # Disable task from being run on app initialization
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
            edi_filename="usage_data",
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
            ),
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
            f"{settings.LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=settings.HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=settings.LITE_API_REQUEST_TIMEOUT,
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
            f"{settings.LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=settings.HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=settings.LITE_API_REQUEST_TIMEOUT,
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
            f"{settings.LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=settings.HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=settings.LITE_API_REQUEST_TIMEOUT,
        )
        self.usage_data.refresh_from_db()
        self.assertIsNone(self.usage_data.lite_sent_at)

    @mock.patch("mail.tasks.schedule_max_tried_task_as_new_task")
    @mock.patch("mail.tasks.Task.objects.get")
    @mock.patch("mail.tasks.put")
    def test_schedule_usages_for_lite_api_max_tried_task(self, put_request, get_task, schedule_new_task):
        put_request.return_value = MockResponse(status_code=HTTP_400_BAD_REQUEST)
        get_task.return_value = MockTask(settings.MAX_ATTEMPTS - 1)
        schedule_new_task.return_value = None

        with self.assertRaises(Exception) as error:
            send_licence_usage_figures_to_lite_api.now(str(self.usage_data.id))

        self.usage_data.refresh_from_db()
        put_request.assert_called_with(
            f"{settings.LITE_API_URL}/licences/hmrc-integration/",
            self.usage_data.lite_payload,
            hawk_credentials=settings.HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=settings.LITE_API_REQUEST_TIMEOUT,
        )
        schedule_new_task.assert_called_with(str(self.usage_data.id))
        self.usage_data.refresh_from_db()
        self.assertIsNone(self.usage_data.lite_sent_at)

    @mock.patch("mail.tasks.send_licence_usage_figures_to_lite_api")
    def test_schedule_new_task(self, send_licence_usage_figures):
        send_licence_usage_figures.return_value = None

        schedule_max_tried_task_as_new_task(str(self.usage_data.id))

        send_licence_usage_figures.assert_called_with(str(self.usage_data.id), schedule=mock.ANY)

    @mock.patch("mail.tasks.put")
    def test_licence_usage_ignore_licence_completion(self, put_request):
        """
        Test that ensures that licenceUsage transaction that has a completion date
        value are not reported to LITE-API because this is an additional transaction
        that is sent when all the allowed quantity of all items on that licence are used.
        Sending it again results in double counting of the recorded usage.
        """
        licence = LicenceIdMapping.objects.create(
            lite_id="5678d9b2-09a9-4e86-840f-236d186e1234", reference="GBSIEL/2020/0000025/P"
        )
        good_mappings = [
            GoodIdMapping.objects.create(
                line_number=(i + 1), lite_id=str(uuid4()), licence_reference="GBSIEL/2020/0000025/P"
            )
            for i in range(3)
        ]

        mail = Mail.objects.create(
            edi_filename="usage_data",
            edi_data=(
                "1\\fileHeader\\CHIEF\\SPIRE\\usageData\\201901130300\\49543\\\n"
                "2\\licenceUsage\\LU04148/00001\\insert\\GBSIEL/2020/0000025/P\\O\\\n"
                "3\\line\\1\\2\\0\\\n"
                "4\\usage\\O\\9GB000001328000-PE112345\\R\\20190112\\2\\0\\\\000262\\\\\\\\\n"
                "5\\end\\line\\5\n"
                "6\\line\\2\\5\\0\\\n"
                "7\\usage\\O\\9GB000001328000-PE112345\\R\\20190112\\5\\0\\\\000262\\\\\\\\\n"
                "8\\end\\line\\5\n"
                "9\\line\\3\\10\\0\\\n"
                "10\\usage\\O\\9GB000001328000-PE112345\\R\\20190112\\10\\0\\\\000262\\\\\\\\\n"
                "11\\end\\line\\5\n"
                "12\\end\\licenceUsage\\10\n"
                "13\\licenceUsage\\LU04148/00002\\insert\\GBSIEL/2020/0000025/P\\C\\20211110\n"
                "14\\line\\1\\2\\0\\\n"
                "15\\end\\line\\2\n"
                "16\\line\\2\\5\\0\\\n"
                "17\\end\\line\\2\n"
                "18\\line\\3\\10\\0\\\n"
                "19\\end\\line\\2\n"
                "20\\end\\licenceUsage\\8\n"
                "21\\fileTrailer\\2"
            ),
        )
        usage_data = UsageData.objects.create(
            mail=mail,
            licence_ids='["GBSIEL/2020/0000025/P"]',
            hmrc_run_number=0,
            spire_run_number=0,
        )

        expected_payload = {
            "usage_data_id": str(usage_data.id),
            "licences": [
                {
                    "id": str(licence.lite_id),
                    "goods": [
                        {"id": str(good_mappings[0].lite_id), "usage": "2", "value": "0", "currency": ""},
                        {"id": str(good_mappings[1].lite_id), "usage": "5", "value": "0", "currency": ""},
                        {"id": str(good_mappings[2].lite_id), "usage": "10", "value": "0", "currency": ""},
                    ],
                    "action": "open",
                    "completion_date": "",
                }
            ],
        }

        put_request.return_value = MockResponse(
            json={
                "licences": {
                    "accepted": [
                        {
                            "id": str(licence.lite_id),
                            "goods": [
                                {"id": str(good_mappings[0].lite_id), "usage": "2"},
                                {"id": str(good_mappings[1].lite_id), "usage": "5"},
                                {"id": str(good_mappings[2].lite_id), "usage": "10"},
                            ],
                        }
                    ],
                    "rejected": [],
                }
            },
            status_code=HTTP_207_MULTI_STATUS,
        )

        send_licence_usage_figures_to_lite_api.now(str(usage_data.id))

        usage_data.refresh_from_db()
        put_request.assert_called_with(
            f"{settings.LITE_API_URL}/licences/hmrc-integration/",
            expected_payload,
            hawk_credentials=settings.HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=settings.LITE_API_REQUEST_TIMEOUT,
        )
        usage_data.refresh_from_db()
        self.assertIsNotNone(usage_data.lite_sent_at)
        self.assertEqual(usage_data.lite_accepted_licences, ["GBSIEL/2020/0000025/P"])
        self.assertEqual(usage_data.lite_rejected_licences, [])

from django.test import tag

from mail.libraries.combine_usage_replies import combine_lite_and_spire_usage_responses
from mail.models import Mail, GoodIdMapping, LicenceIdMapping, UsageUpdate, TransactionMapping
from mail.tests.libraries.client import LiteHMRCTestClient


class CombiningUsageUpdateReplies(LiteHMRCTestClient):
    @tag("combine", "end-to-end")
    def test_combine_two_responses(self):
        edi_data = (
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
            "11\\line\\2\\0\\0\\\n"
            "12\\usage\\O\\9GB000003133000-445251012345\\Z\\20190112\\0\\0\\\\000962\\\\\\\\\n"
            "13\\end\\line\\3\n"
            "14\\end\\licenceUsage\\8\n"
            "15\\licenceUsage\\LU04148/00003\\insert\\GBSIEL/2020/000000X/P\\O\\\n"
            "16\\line\\1\\0\\0\\\n"
            "17\\usage\\O\\9GB000003133000-445251012345\\Z\\20190112\\0\\0\\\\000962\\\\\\\\\n"
            "18\\end\\line\\3\n"
            "19\\end\\licenceUsage\\5\n"
            "20\\fileTrailer\\3"
        )

        lite_response = {
            "usage_update_id": "1e5a4fd0-e581-4efd-9770-ac68e04852d2",
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
        }

        spire_response = (
            "1\\fileHeader\\SPIRE\\CHIEF\\usageReply\\201901130300\\49543\\\n"
            "2\\accepted\\LU04148/00003\n"
            "3\\fileTrailer\\1\\0\\0"
        )

        expected_response = (
            "1\\fileHeader\\SPIRE\\CHIEF\\usageReply\\201901130300\\49543\\\n"
            "2\\accepted\\LU04148/00003\n"
            "3\\accepted\\LU04148/00001\n"
            "4\\rejected\\LU04148/00002\n"
            "5\\error\\5\\Good not found on Licence. in line 11\n"
            "6\\end\\rejected\\3\n"
            "7\\fileTrailer\\2\\1\\0"
        )

        mail = Mail.objects.create(edi_data=edi_data, response_data=spire_response)
        usage_update = UsageUpdate.objects.create(
            lite_response=lite_response, spire_run_number=12345, hmrc_run_number=54321, mail=mail
        )
        LicenceIdMapping.objects.create(
            lite_id="2e6f3fe2-40a2-4c7c-8b71-3f0e53f92298", reference="GBSIEL/2020/0000008/P"
        )
        LicenceIdMapping.objects.create(
            lite_id="80a3d9b2-09a9-4e86-840f-236d186e5b0c", reference="GBSIEL/2020/0000009/P"
        )
        GoodIdMapping.objects.create(
            lite_id="27ac9316-abd0-4dc1-981e-b50714c7fb8c", licence_reference="GBSIEL/2020/0000008/P", line_number=1
        )
        GoodIdMapping.objects.create(
            lite_id="87151418-dfff-4688-ab0c-ff8990db5365", licence_reference="GBSIEL/2020/0000009/P", line_number=2
        )

        TransactionMapping.objects.create(
            usage_transaction="LU04148/00001",
            line_number=1,
            licence_reference="GBSIEL/2020/0000008/P",
            usage_update=usage_update,
        )
        TransactionMapping.objects.create(
            usage_transaction="LU04148/00002",
            line_number=1,
            licence_reference="GBSIEL/2020/0000009/P",
            usage_update=usage_update,
        )
        TransactionMapping.objects.create(
            usage_transaction="LU04148/00002",
            line_number=2,
            licence_reference="GBSIEL/2020/0000009/P",
            usage_update=usage_update,
        )

        result = combine_lite_and_spire_usage_responses(mail=mail)

        self.assertEqual(result, expected_response)

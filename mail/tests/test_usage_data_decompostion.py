import json
import uuid

from django.test import tag

from mail.enums import SourceEnum
from mail.libraries.helpers import get_good_id
from mail.libraries.usage_data_decomposition import (
    build_edifact_file_from_data_blocks,
    split_edi_data_by_id,
    build_json_payload_from_data_blocks,
    id_owner,
)
from mail.models import LicencePayload, GoodIdMapping, UsageUpdate, Mail, TransactionMapping, LicenceIdMapping
from mail.tests.libraries.client import LiteHMRCTestClient


class FileDeconstruction(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

        self.spire_data_expected = [
            ["fileHeader\\CHIEF\\SPIRE\\usageData\\201901130300\\49543\\"],
            [
                "licenceUsage\\LU04148/00001\\insert\\GBOIE2017/12345B\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000001328000-PE112345\\R\\20190112\\0\\0\\\\000262\\\\\\\\",
                "usage\\O\\9GB000001328000-PE112345\\L\\20190112\\0\\0\\\\000262\\\\\\\\",
                "usage\\O\\9GB000001328000-PE112345\\K\\20190112\\0\\0\\\\000262\\\\\\\\",
                "end\\line\\5",
                "end\\licenceUsage\\7",
            ],
            [
                "licenceUsage\\LU04148/00002\\insert\\GBOGE2014/23456\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000003133000-445251012345\\Z\\20190112\\0\\0\\\\000962\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            [
                "licenceUsage\\LU04148/00003\\insert\\GBOGE2018/34567\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000001328000-PE112345\\A\\20190112\\0\\0\\\\000442\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            [
                "licenceUsage\\LU04148/00004\\insert\\GBSIE2018/45678\\O\\",
                "line\\1\\3\\0\\",
                "usage\\O\\9GB00000133000-774170812345\\D\\20190112\\3\\0\\\\009606\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            ["fileTrailer\\7"],
        ]
        self.lite_data_expected = [
            [
                "licenceUsage\\LU04148/00005\\insert\\GBOGE2011/56789\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000004988000-4750437112345\\G\\20190111\\0\\0\\\\000104\\\\\\\\",
                "usage\\O\\9GB000004988000-4750436912345\\Y\\20190111\\0\\0\\\\000104\\\\\\\\",
                "end\\line\\4",
                "end\\licenceUsage\\6",
            ],
            [
                "licenceUsage\\LU04148/00006\\insert\\GBOGE2017/98765\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000002816000-273993\\L\\20190109\\0\\0\\\\000316\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            [
                "licenceUsage\\LU04148/00007\\insert\\GBOGE2015/87654\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000003133000-784920212345\\E\\20190111\\0\\0\\\\000640\\\\\\\\",
                "usage\\O\\9GB000003133000-784918012345\\D\\20190111\\0\\0\\\\000640\\\\\\\\",
                "end\\line\\4",
                "end\\licenceUsage\\6",
            ],
        ]
        self.expected_file_for_spire = (
            "1\\fileHeader\\CHIEF\\SPIRE\\usageData\\201901130300\\49543\\\n"
            "2\\licenceUsage\\LU04148/00001\\insert\\GBOIE2017/12345B\\O\\\n"
            "3\\line\\1\\0\\0\\\n"
            "4\\usage\\O\\9GB000001328000-PE112345\\R\\20190112\\0\\0\\\\000262\\\\\\\\\n"
            "5\\usage\\O\\9GB000001328000-PE112345\\L\\20190112\\0\\0\\\\000262\\\\\\\\\n"
            "6\\usage\\O\\9GB000001328000-PE112345\\K\\20190112\\0\\0\\\\000262\\\\\\\\\n"
            "7\\end\\line\\5\n"
            "8\\end\\licenceUsage\\7\n"
            "9\\licenceUsage\\LU04148/00002\\insert\\GBOGE2014/23456\\O\\\n"
            "10\\line\\1\\0\\0\\\n"
            "11\\usage\\O\\9GB000003133000-445251012345\\Z\\20190112\\0\\0\\\\000962\\\\\\\\\n"
            "12\\end\\line\\3\n"
            "13\\end\\licenceUsage\\5\n"
            "14\\licenceUsage\\LU04148/00003\\insert\\GBOGE2018/34567\\O\\\n"
            "15\\line\\1\\0\\0\\\n"
            "16\\usage\\O\\9GB000001328000-PE112345\\A\\20190112\\0\\0\\\\000442\\\\\\\\\n"
            "17\\end\\line\\3\n"
            "18\\end\\licenceUsage\\5\n"
            "19\\licenceUsage\\LU04148/00004\\insert\\GBSIE2018/45678\\O\\\n"
            "20\\line\\1\\3\\0\\\n"
            "21\\usage\\O\\9GB00000133000-774170812345\\D\\20190112\\3\\0\\\\009606\\\\\\\\\n"
            "22\\end\\line\\3\n"
            "23\\end\\licenceUsage\\5\n"
            "24\\fileTrailer\\7"
        )
        self.expected_lite_json_payload = {
            "licences": [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "goods": [
                        {"id": "00000000-0000-0000-0000-000000000001", "usage": "17", "value": "0", "currency": "",}
                    ],
                },
                {
                    "id": "00000000-0000-0000-0000-000000000002",
                    "goods": [{"id": None, "usage": "0", "value": "0", "currency": ""}],
                },
                {
                    "id": "00000000-0000-0000-0000-000000000003",
                    "goods": [
                        {
                            "id": "00000000-0000-0000-0000-000000000002",
                            "usage": "1000000",
                            "value": "0",
                            "currency": "",
                        }
                    ],
                },
            ]
        }
        """
        [line number (some int)] = 0
        [line start (always usage)] = 1
        [usage_type] = 2
        [declaration-ucr] = 3
        [declaration-part-number] = 4
        [control-date] = 5
        [quantity-used] = 6
        [value-used] = 7
        [trader-id / TURN] = 8
        [claim-ref] = 9
        [origin-country (not used for exports)] = 10
        [customs-mic] = 11
        [customs-message] = 12
        [consignee-name] = 13
        """

    @tag("1022", "id-ident")
    def test_determine_spire_licence_id_and_lite_licence_ids(self):
        spire_id_1 = "GBSIE2018/45678"
        spire_id_2 = "GBOIE2017/12345B"
        lite_id = "GBOGE2011/56789"
        LicencePayload.objects.create(lite_id=uuid.uuid4(), reference=lite_id)
        self.assertEqual(id_owner(spire_id_1), SourceEnum.SPIRE)
        self.assertEqual(id_owner(spire_id_2), SourceEnum.SPIRE)
        self.assertEqual(id_owner(lite_id), SourceEnum.LITE)

    @tag("1022", "splitting-file")
    def test_usage_data_split_according_to_licence_ids(self):
        usage_data = self.licence_usage_file_body.decode("utf-8")
        spire_data_expected = [
            ["fileHeader\\CHIEF\\SPIRE\\usageData\\201901130300\\49543\\"],
            [
                "licenceUsage\\LU04148/00001\\insert\\GBOIE2017/12345B\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000001328000-PE112345\\R\\20190112\\0\\0\\\\000262\\\\\\\\",
                "usage\\O\\9GB000001328000-PE112345\\L\\20190112\\0\\0\\\\000262\\\\\\\\",
                "usage\\O\\9GB000001328000-PE112345\\K\\20190112\\0\\0\\\\000262\\\\\\\\",
                "end\\line\\5",
                "end\\licenceUsage\\7",
            ],
            [
                "licenceUsage\\LU04148/00002\\insert\\GBOGE2014/23456\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000003133000-445251012345\\Z\\20190112\\0\\0\\\\000962\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            [
                "licenceUsage\\LU04148/00003\\insert\\GBOGE2018/34567\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000001328000-PE112345\\A\\20190112\\0\\0\\\\000442\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            [
                "licenceUsage\\LU04148/00004\\insert\\GBSIE2018/45678\\O\\",
                "line\\1\\3\\0\\",
                "usage\\O\\9GB00000133000-774170812345\\D\\20190112\\3\\0\\\\009606\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            [
                "licenceUsage\\LU04148/00005\\insert\\GBOGE2011/56789\\O\\",
                "line\\1\\0\\0\\",
                "usage\\O\\9GB000004988000-4750437112345\\G\\20190111\\0\\0\\\\000104\\\\\\\\",
                "usage\\O\\9GB000004988000-4750436912345\\Y\\20190111\\0\\0\\\\000104\\\\\\\\",
                "end\\line\\4",
                "end\\licenceUsage\\6",
            ],
            ["fileTrailer\\7"],
        ]
        lite_data_expected = [
            [
                "licenceUsage\\LU04148/00006\\insert\\GBSIEL/2020/0000001/P\\O\\",
                "line\\1\\1\\0\\",
                "usage\\O\\9GB000002816000-273993\\L\\20190109\\0\\0\\\\000316\\\\\\\\",
                "end\\line\\3",
                "end\\licenceUsage\\5",
            ],
            [
                "licenceUsage\\LU04148/00007\\insert\\GBSIEL/2020/0000002/P\\O\\",
                "line\\1\\1\\0\\",
                "usage\\O\\9GB000003133000-784920212345\\E\\20190111\\0\\0\\\\000640\\\\\\\\",
                "usage\\O\\9GB000003133000-784918012345\\D\\20190111\\0\\0\\\\000640\\\\\\\\",
                "end\\line\\4",
                "end\\licenceUsage\\6",
            ],
        ]
        LicencePayload.objects.create(lite_id=uuid.uuid4(), reference="GBSIEL/2020/0000002/P")
        spire_data, lite_data = split_edi_data_by_id(usage_data)

        self.assertEqual(spire_data, spire_data_expected)
        self.assertEqual(lite_data, lite_data_expected)

    @tag("1022", "rebuilding-file-spire")
    def test_spire_file_rebuild(self):
        spire_file = build_edifact_file_from_data_blocks(self.spire_data_expected)
        self.assertEqual(spire_file, self.expected_file_for_spire)

    @tag("1022", "build-json-lite")
    def test_lite_json_payload_create(self):
        LicencePayload.objects.create(reference="GBOGE2011/56789", lite_id="00000000-0000-0000-0000-000000000001")
        LicencePayload.objects.create(reference="GBOGE2017/98765", lite_id="00000000-0000-0000-0000-000000000002")
        LicencePayload.objects.create(reference="GBOGE2015/87654", lite_id="00000000-0000-0000-0000-000000000003")
        self.lite_data_expected[0] = [
            "licenceUsage\\LU04148/00005\\insert\\GBOGE2011/56789\\O\\",
            "line\\2\\17\\0\\",
        ]
        self.lite_data_expected[2] = [
            "licenceUsage\\LU04148/00007\\insert\\GBOGE2015/87654\\O\\",
            "line\\1\\1000000\\0\\",
        ]
        GoodIdMapping.objects.create(
            licence_reference="GBOGE2011/56789", line_number=2, lite_id="00000000-0000-0000-0000-000000000001",
        )
        GoodIdMapping.objects.create(
            licence_reference="GBOGE2015/87654", line_number=1, lite_id="00000000-0000-0000-0000-000000000002",
        )
        lite_payload = build_json_payload_from_data_blocks(self.lite_data_expected)

        self.assertEqual(lite_payload, self.expected_lite_json_payload)

    @tag("de-mapping-goods")
    def test_de_mapping_goods(self):
        licence_reference = "GB2020/00001/SIE/P"
        lite_good_id = "00000000-0000-0000-0000-000000000001"
        line_number = 1
        GoodIdMapping.objects.create(lite_id=lite_good_id, line_number=line_number, licence_reference=licence_reference)

        self.assertEqual(get_good_id(line_number=line_number, licence_reference=licence_reference), lite_good_id)

    @tag("create-transaction-mapping")
    def test_create_transaction_mapping_for_lite_licences(self):
        usage_data = self.licence_usage_file_body.decode("utf-8")
        LicenceIdMapping.objects.create(
            lite_id="00000000-0000-0000-0000-000000000001", reference="GBSIEL/2020/0000002/P"
        )
        split_edi_data_by_id(
            usage_data, UsageUpdate.objects.create(mail=Mail.objects.create(), spire_run_number=1, hmrc_run_number=1)
        )

        self.assertEqual(TransactionMapping.objects.count(), 2)

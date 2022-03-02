import logging

from django.conf import settings
from django.test import tag
from parameterized import parameterized

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum, UnitMapping
from mail.libraries.helpers import (
    convert_sender_to_source,
    convert_source_to_sender,
    new_hmrc_run_number,
    get_run_number,
    map_unit,
    get_action,
    process_attachment,
    get_country_id,
)
from mail.libraries.lite_to_edifact_converter import get_transaction_reference
from mail.models import LicenceData, Mail
from mail.tests.libraries.client import LiteHMRCTestClient


class HelpersTests(LiteHMRCTestClient):
    @parameterized.expand([[settings.SPIRE_ADDRESS, SourceEnum.SPIRE], ["LITE", "LITE"]])
    def test_convert_sender_to_source(self, sender, source):
        self.assertEqual(convert_sender_to_source(sender), source)

    @parameterized.expand([[settings.SPIRE_ADDRESS, SourceEnum.SPIRE], ["LITE", "LITE"]])
    def test_convert_source_to_sender(self, sender, source):
        self.assertEqual(convert_source_to_sender(source), sender)

    @parameterized.expand([[5, 4, 5], [1234568, 34567, 34568], [0, 99999, 0], [7, 7, 7]])
    def test_new_hmrc_run_number(self, source, old, new):
        mail = self._setup_mail()
        LicenceData.objects.create(
            mail=mail,
            hmrc_run_number=old,
            source_run_number=old,
            source=SourceEnum.SPIRE,
        )
        self.assertEqual(new_hmrc_run_number(source), new)

    @parameterized.expand(
        [
            [["name", b"data"], "name", "data"],
            [[], "", ""],
            [["something"], "", ""],
            ["something", "", ""],
        ]
    )
    def test_process_attachment(self, attachment, attachment_name, attachment_data):
        self.assertEqual((attachment_name, attachment_data), process_attachment(attachment))

    def test_get_run_number_from_subject(self):
        subject = "ILBDOTI_live_CHIEF_usageData_9876_201901130300"
        run_number = get_run_number(subject)
        self.assertEqual(run_number, 9876)

    def value_error_thrown_cannot_find_run_number(self):
        subject = "usageData_9876_201901130300"
        with self.assertRaises(ValueError) as context:
            get_run_number(subject)
        self.assertEqual("Can not find valid run-number", str(context.exception))

    def value_error_thrown_run_number_wrong_format(self):
        subject = "abc_xyz_nnn_yyy_a1b34_datetime"
        with self.assertRaises(ValueError) as context:
            get_run_number(subject)
        self.assertEqual("Can not find valid run-number", str(context.exception))

    @staticmethod
    def _setup_mail():
        return Mail.objects.create(
            edi_data="blank",
            extract_type=ExtractTypeEnum.USAGE_DATA,
            status=ReceptionStatusEnum.PENDING,
            edi_filename="blank",
        )

    @parameterized.expand(
        [
            ("NAR", 30),
            ("GRM", 21),
            ("KGM", 23),
            ("MTK", 45),
            ("MTR", 57),
            ("LTR", 94),
            ("MTQ", 2),
            ("ITG", 30),
        ]
    )
    @tag("2448", "unit")
    def test_convert(self, lite_input, output):
        self.assertEqual(output, UnitMapping.convert(lite_input))

    @parameterized.expand(
        [
            ("NAR", 30),
            ("GRM", 21),
            ("KGM", 23),
            ("MTK", 45),
            ("MTR", 57),
            ("LTR", 94),
            ("MTQ", 2),
            ("ITG", 30),
        ]
    )
    @tag("2448", "mapping")
    def test_mapping(self, lite_input, output):
        data = {"goods": [{"unit": lite_input}]}
        self.assertEqual(output, map_unit(data, 0)["goods"][0]["unit"])

    @parameterized.expand([("GB/00001/P", "00001P"), ("GB/001/P/A", "001PA"), ("GB/0/01/P/a", "001Pa")])
    @tag("1917", "transaction-ref")
    def test_transaction_reference_for_licence_data(self, reference, transaction_reference):
        self.assertEqual(get_transaction_reference(reference), transaction_reference)

    @parameterized.expand([("O", "open"), ("E", "exhaust"), ("D", "expire"), ("S", "surrender"), ("C", "cancel")])
    @tag("1917", "action-ref")
    def test_action_reference_for_usage(self, reference, action):
        self.assertEqual(get_action(reference), action)

    @parameterized.expand(
        [
            ("GB", "GB"),
            ('{"id": "GB"}', "GB"),
            ({"id": "GB"}, "GB"),
            ("AE-DU", "AE"),
            ({"id": "AE-DU"}, "AE"),
        ]
    )
    @tag("country-id")
    def test_get_country_id(self, country, id):
        self.assertEqual(get_country_id(country), id)


def print_all_mails():
    all_mails = Mail.objects.all()
    for mail in all_mails:
        rec = {
            "id": mail.id,
            "edi_filename": mail.edi_filename,
            "status": mail.status,
            "extract_type": mail.extract_type,
        }
        logging.debug("Mail -> {}".format(rec))

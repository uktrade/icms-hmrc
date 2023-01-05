from parameterized import parameterized

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.libraries.helpers import get_country_id
from mail.libraries.lite_to_edifact_converter import get_transaction_reference
from mail.models import Mail
from mail.tests.libraries.client import LiteHMRCTestClient


class HelpersTests(LiteHMRCTestClient):
    @staticmethod
    def _setup_mail():
        return Mail.objects.create(
            edi_data="blank",
            extract_type=ExtractTypeEnum.USAGE_DATA,
            status=ReceptionStatusEnum.PENDING,
            edi_filename="blank",
        )

    @parameterized.expand([("GB/00001/P", "00001P"), ("GB/001/P/A", "001PA"), ("GB/0/01/P/a", "001Pa")])
    def test_transaction_reference_for_licence_data(self, reference, transaction_reference):
        self.assertEqual(get_transaction_reference(reference), transaction_reference)

    @parameterized.expand(
        [
            ("GB", "GB"),
            ('{"id": "GB"}', "GB"),
            ({"id": "GB"}, "GB"),
            ("AE-DU", "AE"),
            ({"id": "AE-DU"}, "AE"),
        ]
    )
    def test_get_country_id(self, country, id):
        self.assertEqual(get_country_id(country), id)

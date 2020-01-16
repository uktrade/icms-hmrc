from parameterized import parameterized

from conf.test_client import LiteHMRCTestClient
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.models import LicenceUpdate, Mail
from mail.services.helpers import (
    convert_sender_to_source,
    convert_source_to_sender,
    new_hmrc_run_number,
)


class HelpersTests(LiteHMRCTestClient):
    @parameterized.expand([["test@spire.com", "SPIRE"], ["test@lite.com", "LITE"]])
    def test_convert_sender_to_source(self, sender, source):
        self.assertEqual(convert_sender_to_source(sender), source)

    @parameterized.expand([["test@spire.com", "SPIRE"], ["test@lite.com", "LITE"]])
    def test_convert_source_to_sender(self, sender, source):
        self.assertEqual(convert_source_to_sender(source), sender)

    @parameterized.expand(
        [[5, 4, 5], [1234568, 34567, 34568], [0, 99999, 0], [7, 7, 7]]
    )
    def test_new_hmrc_run_number(self, source, old, new):
        mail = self._setup_mail()
        LicenceUpdate.objects.create(
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
        pass

    @staticmethod
    def _setup_mail():
        return Mail.objects.create(
            edi_data="blank",
            extract_type=ExtractTypeEnum.INSERT,
            status=ReceptionStatusEnum.ACCEPTED,
            edi_filename="blank",
        )

from mail import models
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.tests.libraries.client import LiteHMRCTestClient


class DataProcessorsTestBase(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()
        self.hmrc_run_number = 28
        self.source_run_number = 28
        self.licence_ids = "GBOIE2017/12345B"

        self.mail = models.Mail.objects.create(
            edi_data=self.licence_data_file_body,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            status=ReceptionStatusEnum.PENDING,
            edi_filename=self.licence_data_file_name,
        )

        self.licence_data = models.LicenceData.objects.create(
            mail=self.mail,
            hmrc_run_number=self.hmrc_run_number,
            source_run_number=self.source_run_number,
            licence_ids=self.licence_ids,
            source=SourceEnum.SPIRE,
        )

        self.usage_mail = models.Mail.objects.create(
            edi_filename=self.licence_usage_file_name,
            edi_data=self.licence_usage_file_body,
            extract_type=ExtractTypeEnum.USAGE_DATA,
            status=ReceptionStatusEnum.PENDING,
        )

        self.usage_data = models.UsageData.objects.create(
            mail=self.usage_mail,
            spire_run_number=self.source_run_number,
            licence_ids=self.licence_ids,
            hmrc_run_number=self.hmrc_run_number,
        )

from conf.test_client import LiteHMRCTestClient
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, SourceEnum
from mail.models import Mail, LicenceUpdate, UsageUpdate


class DataProcessorsTestBase(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()
        self.hmrc_run_number = 28
        self.source_run_number = 15
        self.license_ids = "GBOIE2017/12345B"

        self.mail = Mail.objects.create(
            edi_data=self.licence_update_file_body,
            extract_type=ExtractTypeEnum.LICENCE_UPDATE,
            status=ReceptionStatusEnum.PENDING,
            edi_filename=self.licence_update_file_name,
        )

        self.licence_update = LicenceUpdate.objects.create(
            mail=self.mail,
            hmrc_run_number=self.hmrc_run_number,
            source_run_number=self.source_run_number,
            license_ids=self.license_ids,
            source=SourceEnum.SPIRE,
        )

        self.usage_mail = Mail.objects.create(
            edi_filename=self.licence_usage_file_name,
            edi_data=self.licence_usage_file_body,
            extract_type=ExtractTypeEnum.USAGE_UPDATE,
            status=ReceptionStatusEnum.PENDING,
        )

        self.usage_update = UsageUpdate.objects.create(
            mail=self.usage_mail,
            spire_run_number=self.source_run_number,
            license_ids=self.license_ids,
            hmrc_run_number=self.hmrc_run_number,
        )

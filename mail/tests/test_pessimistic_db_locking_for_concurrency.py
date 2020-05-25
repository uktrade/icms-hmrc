import threading

from conf.settings import SYSTEM_INSTANCE_UUID
from conf.test_client import LiteHMRCTestClient
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.models import Mail
from mail.services.data_processors import lock_db_for_sending_transaction


class PessimisticDbLockingTests(LiteHMRCTestClient):
    def setUp(self):
        super().setUp()

        self.mail = Mail.objects.create(
            edi_data=self.licence_usage_file_body,
            extract_type=ExtractTypeEnum.USAGE_UPDATE,
            status=ReceptionStatusEnum.PENDING,
            edi_filename=self.licence_usage_file_name,
        )

    def test_thread_locks_sending(self):
        val = lock_db_for_sending_transaction(self.mail)
        self.mail.refresh_from_db()
        self.assertTrue(val)
        self.assertEqual(
            self.mail.currently_processed_by,
            str(SYSTEM_INSTANCE_UUID) + "-" + str(threading.currentThread().ident),
        )

    def test_expired_lock_can_be_overridden(self):
        mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.USAGE_UPDATE,
            status=ReceptionStatusEnum.PENDING,
        )
        mail.currently_processed_by = "1234567890"
        mail.set_locking_time(offset=-125)
        val = lock_db_for_sending_transaction(mail)

        mail.refresh_from_db()
        self.assertTrue(val)
        self.assertEqual(
            mail.currently_processed_by,
            str(SYSTEM_INSTANCE_UUID) + "-" + str(threading.currentThread().ident),
        )

    def test_unexpired_lock_cannot_be_overriden(self):
        mail = Mail.objects.create(
            extract_type=ExtractTypeEnum.USAGE_UPDATE,
            status=ReceptionStatusEnum.PENDING,
        )
        mail.currently_processed_by = "1234567890"
        mail.set_locking_time()

        val = lock_db_for_sending_transaction(mail)

        mail.refresh_from_db()
        self.assertFalse(val)
        self.assertEqual(
            mail.currently_processed_by, "1234567890",
        )

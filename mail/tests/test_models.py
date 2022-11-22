import uuid
from unittest.mock import create_autospec

import pytest
from django.test import override_settings
from django.utils import timezone

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum, ReplyStatusEnum
from mail.models import LicencePayload, Mail


class TestSendNotifyEmail:
    @pytest.fixture(autouse=True)
    def _setup(self, db, monkeypatch):
        self.mock_notify_users = create_autospec(spec=Mail.notify_users)

        # # Create a mail object that is waiting for a licence reply from HMRC
        self.mail = Mail.objects.create(
            status=ReceptionStatusEnum.REPLY_PENDING,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename="the_licence_data_file",
            edi_data="lovely data",
            sent_filename="the_licence_data_file",
            sent_data="lovely data",
        )

        monkeypatch.setattr(self.mail, "notify_users", self.mock_notify_users)

    @override_settings(SEND_REJECTED_EMAIL=True)
    def test_notify_users_called_when_setting_enabled(self):
        self.mail.response_data = f"test {ReplyStatusEnum.REJECTED}"
        self.mail.response_date = timezone.now()
        self.mail.save()

        self.mock_notify_users.assert_called_with(self.mail.id, self.mail.response_date)

    @override_settings(SEND_REJECTED_EMAIL=True)
    def test_notify_users_not_called_when_setting_enabled_but_response_accepted(self):
        self.mail.response_data = f"test {ReplyStatusEnum.ACCEPTED}"
        self.mail.response_date = timezone.now()
        self.mail.save()

        self.mock_notify_users.assert_not_called()

    @override_settings(SEND_REJECTED_EMAIL=False)
    def test_notify_users_not_called_when_setting_disabled(self):
        self.mail.response_data = f"test {ReplyStatusEnum.REJECTED}"
        self.mail.response_date = timezone.now()
        self.mail.save()

        self.mock_notify_users.assert_not_called()


def test_licence_payload_model__str__():
    lite_id = uuid.uuid4()
    lp = LicencePayload(lite_id=lite_id, reference="IMA/2022/00001", action="insert")

    assert f"LicencePayload(lite_id={lite_id}, reference=IMA/2022/00001, action=insert)" == str(lp)

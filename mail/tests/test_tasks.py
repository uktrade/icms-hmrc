import pathlib
import poplib
import uuid
from http import HTTPStatus
from typing import TYPE_CHECKING, List
from unittest import mock
from urllib import parse

import msal
import pytest
from django.conf import settings
from django.test import override_settings

from mail import auth, servers, tasks
from mail.enums import (
    ChiefSystemEnum,
    ExtractTypeEnum,
    FakeChiefLicenceReplyEnum,
    LicenceActionEnum,
    MailStatusEnum,
)
from mail.models import LicenceData, LicencePayload, Mail, SourceEnum
from mail.utils import pop3

if TYPE_CHECKING:
    from requests_mock import Mocker


@pytest.fixture(autouse=True)
def icms_source():
    """Ensure all tests have the CHIEF_SOURCE_SYSTEM set to ICMS"""
    with override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS):
        yield


@pytest.fixture
def mock_pop3():
    """Mock pop3 to return a known response (CHIEF_licenceReply_29236_202209231140.eml)"""

    mock_pop3 = mock.create_autospec(spec=poplib.POP3_SSL)

    # The return value of calling a magic mock is another instance of the mock with the same spec
    # mock = mock.create_autospec(spec=SomeClass)
    # mock.return_value == mock()
    # Therefore we need to mock the methods on the return_value attribute
    # See here: https://docs.python.org/3/library/unittest.mock.html#calling
    mock_pop3.return_value.list.return_value = (b"+OK", [b"1 12345"], 1234)

    filename = "CHIEF_licenceReply_29236_202209231140.eml"
    mock_pop3.return_value.retr.return_value = (b"+OK", get_licence_reply_msg_list(filename), 1234)

    return mock_pop3


@pytest.fixture
def mock_msal_client():
    client = mock.create_autospec(spec=msal.ConfidentialClientApplication)

    return client


@pytest.fixture
def mock_pop3_multiple_attachments(mock_pop3):
    """Override mock_pop3 to return an email with multiple attachments."""

    filename = "CHIEF_licenceReply_29237_202209241020-two-attachments.eml"
    mock_pop3.return_value.retr.return_value = (b"+OK", get_licence_reply_msg_list(filename), 1234)

    return mock_pop3


@pytest.fixture
def mock_pop3_unknown_subject(mock_pop3):
    """Override mock_pop3 to return an email with an unknown subject."""

    filename = "CHIEF_licenceReply_29238_202209251140-unknown-subject.eml"
    mock_pop3.return_value.retr.return_value = (b"+OK", get_licence_reply_msg_list(filename), 1234)

    return mock_pop3


@pytest.fixture
def mock_pop3_invalid_reply_subject(mock_pop3):
    """Override mock_pop3 to return an email with an invalid subject for a licenceReply email."""

    filename = "CHIEF_licenceReply_29238_202209251140-invalid-reply-subject.eml"
    mock_pop3.return_value.retr.return_value = (b"+OK", get_licence_reply_msg_list(filename), 1234)

    return mock_pop3


@pytest.fixture
def mock_pop3_usage(mock_pop3):
    filename = "ILBDOTI_live_CHIEF_usageData_7132_202209280300.eml"
    mock_pop3.return_value.retr.return_value = (b"+OK", get_licence_reply_msg_list(filename), 1234)

    return mock_pop3


@pytest.fixture()
def correct_email_settings():
    """Correct test email settings"""
    with override_settings(HMRC_TO_DIT_EMAIL_USER="chief"):
        yield None


@pytest.fixture
def valid_licence_reply() -> str:
    filename = "mail/tests/files/icms/licence_reply/accepted_and_rejected_example"
    return pathlib.Path(filename).read_text()


@pytest.fixture
def partially_valid_licence_reply() -> str:
    filename = "mail/tests/files/icms/licence_reply/partially_valid_example"
    return pathlib.Path(filename).read_text()


def test_can_mock_email(mock_pop3):
    con = mock_pop3("dummy-host")

    ids = pop3.list_messages_ids(con)
    assert ids == ["1"]

    email = pop3.get_email(con, "1")
    assert email.get("Subject") == "CHIEF_licenceReply_29236_202209231140"

    attachments = list(email.iter_attachments())
    reply_file = attachments[0]
    file_name = reply_file.get_filename()

    assert file_name == "CHIEF_licenceReply_29236_202209231140"

    expected_file = TestProcessLicenceReplyAndUsageEmailTask.get_expected_file()

    actual_file = reply_file.get_payload(decode=True).decode()

    assert expected_file == actual_file


class TestProcessLicenceReplyAndUsageEmailTask:
    @pytest.fixture(autouse=True)
    def _setup(self, db, monkeypatch, mock_msal_client):
        self.con = None
        self.monkeypatch = monkeypatch

        # Create a mail object that is waiting for a licence reply from HMRC
        self.mail = Mail.objects.create(
            status=MailStatusEnum.REPLY_PENDING,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename="the_licence_data_file",
            edi_data="lovely data",
        )
        LicenceData.objects.create(
            licence_ids="", hmrc_run_number=29236, source=SourceEnum.ICMS, mail=self.mail
        )
        self.monkeypatch.setattr(auth.msal, "ConfidentialClientApplication", mock_msal_client)

    def _patch_pop3_class(self, mock):
        # Store con reference to check what was called later
        self.con = mock.return_value

        # Patch where the pop3 connection is made
        self.monkeypatch.setattr(servers.poplib, "POP3_SSL", mock)

    @staticmethod
    def get_expected_file() -> str:
        filename = "mail/tests/files/icms/CHIEF_licenceReply_29236_202209231140_attachment"
        return pathlib.Path(filename).read_text()

    @staticmethod
    def get_expected_usage_file() -> str:
        filename = "mail/tests/files/icms/ILBDOTI_live_CHIEF_usageData_7132_202209280300_attachment"
        return pathlib.Path(filename).read_text()

    def test_process_licence_reply_email_success(self, correct_email_settings, mock_pop3):
        self._patch_pop3_class(mock_pop3)

        # Check for emails and process them
        tasks.process_licence_reply_and_usage_emails()

        # Test the licence mail has been updated with the response email
        mail = LicenceData.objects.get(hmrc_run_number=29236).mail
        assert mail.status == MailStatusEnum.REPLY_RECEIVED
        assert mail.response_filename == "CHIEF_licenceReply_29236_202209231140"
        assert mail.response_data == self.get_expected_file()

        # Successful processing should delete the message
        self.con.dele.assert_called_with("1")

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

    def test_process_licence_reply_errors_with_multiple_attachments(
        self, correct_email_settings, mock_pop3_multiple_attachments
    ):
        self._patch_pop3_class(mock_pop3_multiple_attachments)

        # Only one attachment is accepted per licence reply email.
        with pytest.raises(
            ValueError, match="Only one attachment is accepted per licence reply email."
        ):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

    def test_process_licence_reply_errors_with_invalid_reply_subject(
        self, correct_email_settings, mock_pop3_invalid_reply_subject
    ):
        self._patch_pop3_class(mock_pop3_invalid_reply_subject)

        with pytest.raises(
            ValueError,
            match="Unable to parse run number from 'CHIEF_licenceReply_INVALID_29236_202209231140'",
        ):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

    def test_process_usage_email_success(self, correct_email_settings, mock_pop3_usage):
        self._patch_pop3_class(mock_pop3_usage)

        # Check for emails and process them
        tasks.process_licence_reply_and_usage_emails()

        # Test the licence mail has been updated with the response email
        mail = Mail.objects.get(response_filename="ILBDOTI_live_CHIEF_usageData_7132_202209280300")
        assert mail.extract_type == ExtractTypeEnum.USAGE_DATA
        assert mail.status == MailStatusEnum.REPLY_RECEIVED
        assert mail.response_subject == "ILBDOTI_live_CHIEF_usageData_7132_202209280300"
        assert mail.response_data == self.get_expected_usage_file()

        # Successful processing should delete the message
        self.con.dele.assert_called_with("1")

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

    def test_rollback_when_we_get_an_error_in_one_of_the_files(
        self, correct_email_settings, transactional_db
    ):
        """Test a scenario where there is a good licence file and a bad usage file.

        Everything should roll back if we can't process everything.
        """

        mock_pop3_cls = mock.create_autospec(spec=poplib.POP3_SSL)
        # Return multiple message id's (licenceReply and Usage)
        mock_pop3_cls.return_value.list.return_value = (b"+OK", [b"1 12345", b"2 54321"], 1234)

        def mock_retr(msg_id):
            if msg_id == "1":
                return (
                    b"+OK",
                    get_licence_reply_msg_list("CHIEF_licenceReply_29236_202209231140.eml"),
                    12345,
                )

            if msg_id == "2":
                return (
                    b"+OK",
                    get_licence_reply_msg_list(
                        "ILBDOTI_live_CHIEF_usageData_7132_202209280300.eml"
                    ),
                    54321,
                )

        mock_pop3_cls.return_value.retr = mock_retr
        self._patch_pop3_class(mock_pop3_cls)

        # Let's make the _save_usage_data_email fail with a custom error
        mock__save_usage_data_email = mock.create_autospec(
            spec=tasks._save_usage_data_email,
            side_effect=RuntimeError("Something unexpected has happened..."),
        )

        self.monkeypatch.setattr(tasks, "_save_usage_data_email", mock__save_usage_data_email)

        with pytest.raises(RuntimeError, match="Something unexpected has happened..."):
            tasks.process_licence_reply_and_usage_emails()

        # The licenceReply mail should have processed correctly and therefore the mail would be marked for deletion
        self.con.dele.assert_called_once()
        self.con.dele.assert_called_with("1")

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

        # Check the Mail model changes have been rolled back (as the task errored)
        self.mail.refresh_from_db()
        assert self.mail.status == MailStatusEnum.REPLY_PENDING
        assert not self.mail.response_filename
        assert not self.mail.response_data

    @override_settings(
        HMRC_TO_DIT_EMAIL_USER="chief", HMRC_TO_DIT_EMAIL_HOSTNAME="fake-valid-domain.com"
    )
    def test_unknown_email_sender_domain(self, mock_pop3):
        self._patch_pop3_class(mock_pop3)

        with pytest.raises(
            ValueError,
            match=(
                'Unable to verify incoming email: From:"HMRC, CHIEF" <chief@hmrc_test_email.com>, '
                "Subject: CHIEF_licenceReply_29236_202209231140"
            ),
        ):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

    @override_settings(
        HMRC_TO_DIT_EMAIL_USER="fake-valid-user", HMRC_TO_DIT_EMAIL_HOSTNAME="hmrc_test_email.com"
    )
    def test_unknown_email_sender_user(self, mock_pop3):
        self._patch_pop3_class(mock_pop3)

        with pytest.raises(
            ValueError,
            match=(
                'Unable to verify incoming email: From:"HMRC, CHIEF" <chief@hmrc_test_email.com>, '
                "Subject: CHIEF_licenceReply_29236_202209231140"
            ),
        ):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()


# Note: Only added this test to cover a "partial" coverage line.
def test_get_run_number_from_unknown_subject():
    with pytest.raises(ValueError, match="Unable to parse run number from 'unknown_subject'"):
        tasks._get_run_number_from_subject("unknown_subject")


def get_licence_reply_msg_list(filename: str) -> List[bytes]:
    return pathlib.Path(f"mail/tests/files/icms/{filename}").read_bytes().split(b"\r\n")


@mock.patch("mail.requests.hawk_authentication_enabled", lambda: True)
class TestSendLicenceDataToICMSTask:
    @pytest.fixture(autouse=True)
    def _setup(self, transactional_db, requests_mock: "Mocker", valid_licence_reply):
        self.rq = requests_mock

        # Create a mail object that has data to send to ICMS
        self.mail = Mail.objects.create(
            status=MailStatusEnum.REPLY_RECEIVED,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename="the_licence_data_file",
            edi_data="lovely data",
            response_filename="CHIEF_licenceReply_29236_202209231140",
            response_data=valid_licence_reply,
        )
        ld = LicenceData.objects.create(
            licence_ids="", hmrc_run_number=29236, source=SourceEnum.ICMS, mail=self.mail
        )

        # fake some licence payload references for the test file
        for reference in ["ABC12345", "ABC12346", "ABC12348", "ABC12347"]:
            payload = LicencePayload.objects.create(
                icms_id=uuid.uuid4(),
                reference=reference,
                action=LicenceActionEnum.INSERT,
                is_processed=True,
            )
            ld.licence_payloads.add(payload)

        # Store the ICMS UUID that was sent from ICMS.
        self.id_1 = str(LicencePayload.objects.get(reference="ABC12345").icms_id)
        self.id_2 = str(LicencePayload.objects.get(reference="ABC12346").icms_id)
        self.id_3 = str(LicencePayload.objects.get(reference="ABC12348").icms_id)
        self.id_4 = str(LicencePayload.objects.get(reference="ABC12347").icms_id)

    def test_send_licence_data_to_icms_success(self, caplog):
        # Mock the response that ICMS sends back
        url = parse.urljoin(settings.ICMS_API_URL, "chief/license-data-callback")
        self.rq.post(url, status_code=HTTPStatus.OK, json={})

        with mock.patch("mail.requests.verify_api_response", spec=True) as verify_resp:
            # Send the licence data to ICMS
            tasks.send_licence_data_to_icms()

            verify_resp.assert_called_once()

        self.mail.refresh_from_db()

        # Check the hawk headers is there
        assert "hawk-authentication" in self.rq.last_request.headers

        # Check the mail has been updated
        assert self.mail.status == MailStatusEnum.REPLY_PROCESSED

        # Check what data we sent to ICMS
        assert self.rq.last_request.json() == {
            "accepted": [{"id": self.id_1}, {"id": self.id_2}, {"id": self.id_3}],
            "rejected": [
                {
                    "id": self.id_4,
                    "errors": [
                        {"error_code": "1234", "error_msg": "Invalid thingy"},
                        {
                            "error_code": "76543",
                            "error_msg": "Invalid commodity “1234A6” in line " "23",
                        },
                    ],
                }
            ],
            "run_number": "29236",
        }

        last_log_msg = caplog.messages[-1]
        assert last_log_msg == (
            f"Successfully sent mail (id: {self.mail.id}, filename: {self.mail.response_filename})"
            f" to ICMS for processing"
        )

    def test_send_licence_data_to_icms_success_with_partially_valid_file(
        self, partially_valid_licence_reply
    ):
        # Setup
        self.mail.response_data = partially_valid_licence_reply
        self.mail.save()
        # Mock the response that ICMS sends back
        url = parse.urljoin(settings.ICMS_API_URL, "chief/license-data-callback")
        self.rq.post(url, status_code=HTTPStatus.OK, json={})

        # Test
        with (
            mock.patch("mail.requests.verify_api_response", spec=True) as verify_resp,
            mock.patch("mail.tasks.capture_message", spec=True) as mock_capture_message,
        ):
            # Send the licence data to ICMS
            tasks.send_licence_data_to_icms()

            verify_resp.assert_called_once()
            mock_capture_message.assert_called_with(
                f"Successfully sent mail (id: {self.mail.id}, filename: {self.mail.response_filename}) to ICMS for processing but not all records were processed.",
                "error",
            )

        self.mail.refresh_from_db()

        # Check the hawk headers is there
        assert "hawk-authentication" in self.rq.last_request.headers

        # Check the mail has been updated
        assert self.mail.status == MailStatusEnum.REPLY_PARTIALLY_PROCESSED

        # Check what data we sent to ICMS (less than the success test)
        assert self.rq.last_request.json() == {
            "accepted": [{"id": self.id_1}, {"id": self.id_2}],
            "rejected": [],
            "run_number": "29236",
        }

    def test_send_licence_data_to_icms_http_error(self, caplog):
        # Mock the response that ICMS sends back - an internal server error
        url = parse.urljoin(settings.ICMS_API_URL, "chief/license-data-callback")
        self.rq.post(
            url, status_code=HTTPStatus.INTERNAL_SERVER_ERROR, json={}, reason="test reason"
        )

        # Send the licence data to ICMS using the data we know should pass
        with mock.patch("mail.requests.verify_api_response", spec=True) as verify_resp:
            # Send the licence data to ICMS
            tasks.send_licence_data_to_icms()

            verify_resp.assert_called_once()

        last_log_msg = caplog.messages[-1]
        assert last_log_msg == (
            "Failed to send licence reply data to ICMS (Check ICMS sentry):"
            " 500 Server Error: test reason for url: http://caseworker:8008/chief/license-data-callback"
        )

        # Check the mail status hasn't changed
        self.mail.refresh_from_db()

        assert self.mail.status == MailStatusEnum.REPLY_RECEIVED


def test_no_mail_found(db, caplog):
    tasks.send_licence_data_to_icms()

    assert caplog.messages == [
        "Checking for licence data to send to ICMS",
        "No licence date found to send to ICMS",
    ]


def test_multiple_mail_raises_error(db, valid_licence_reply):
    Mail.objects.create(
        status=MailStatusEnum.REPLY_RECEIVED,
        extract_type=ExtractTypeEnum.LICENCE_DATA,
        edi_filename="the_licence_data_file",
        edi_data="lovely data",
        response_filename="CHIEF_licenceReply_29236_202209231140",
        response_data=valid_licence_reply,
    )

    Mail.objects.create(
        status=MailStatusEnum.REPLY_RECEIVED,
        extract_type=ExtractTypeEnum.LICENCE_DATA,
        edi_filename="the_licence_data_file",
        edi_data="lovely data",
        response_filename="CHIEF_licenceReply_29237_202209231140",
        response_data=valid_licence_reply,
    )

    with pytest.raises(
        ValueError, match="Unable to process mail as there are more than 1 records."
    ):
        tasks.send_licence_data_to_icms()


def test_file_with_only_errors_raises_errors(db, caplog):
    mail = Mail.objects.create(
        status=MailStatusEnum.REPLY_RECEIVED,
        extract_type=ExtractTypeEnum.LICENCE_DATA,
        edi_filename="the_licence_data_file",
        edi_data="lovely data",
        response_filename="CHIEF_licenceReply_29237_202209231140",
    )

    file_with_file_error = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\fileError\\18\\Record type 'fileHeader' not recognised\\99\n"
        "3\\fileTrailer\\0\\0\\1\n"
    )

    mail.response_data = file_with_file_error
    mail.save()

    with pytest.raises(
        ValueError,
        match=rf"Unable to process mail \(id: {mail.id}, filename: {mail.response_filename}\) as it has file errors.",
    ):
        tasks.send_licence_data_to_icms()

        assert caplog.messages == [
            "Checking for licence data to send to ICMS",
            f"Unable to process mail (id: {mail.id}, filename: {mail.response_filename}) as it has file errors.",
            "File error: position: 99, code: 18, error_msg: Record type 'fileHeader' not recognised",
        ]

    file_with_file_error_and_file_trailer_errors = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\fileError\\18\\Record type 'fileHeader' not recognised\\99\n"
        "3\\fileTrailer\\0\\1\\1\n"
    )
    mail.response_data = file_with_file_error_and_file_trailer_errors
    mail.save()
    with pytest.raises(
        ValueError,
        match=rf"Unable to process mail \(id: {mail.id}, filename: {mail.response_filename}\) as it has file errors.",
    ):
        tasks.send_licence_data_to_icms()

        assert caplog.messages == [
            "Checking for licence data to send to ICMS",
            f"Unable to process mail (id: {mail.id}, filename: {mail.response_filename}) as it has file errors.",
            "File error: position: 99, code: 18, error_msg: Record type 'fileHeader' not recognised",
            "File trailer count is different from processor count of accepted and rejected",
        ]


class TestSendLicenceDataToHMRC:
    @pytest.fixture(autouse=True)
    def _setup(self, db):
        ...  # fmt: skip

    def test_task_is_called(self, caplog):
        tasks.send_licence_data_to_hmrc()

        assert caplog.messages == [
            "Sending ICMS licence updates to HMRC",
            "There are currently no licences to send",
        ]


class TestFakeLicenceReply:
    @pytest.fixture(autouse=True)
    def _setup(self, db):
        ...  # fmt: skip

    @override_settings(DEBUG=True, ICMS_FAKE_HMRC_REPLY=FakeChiefLicenceReplyEnum.ACCEPT)
    def test_task_is_called(self, caplog, capsys):
        tasks.fake_licence_reply()

        captured = capsys.readouterr()
        assert captured.out.split("\n") == [
            "Desired outcome: accept",
            "No mail records with reply_pending status",
            "",
        ]

    @override_settings(APP_ENV="production")
    def test_run_in_prod_returns_early(self, caplog):
        tasks.fake_licence_reply()

        assert caplog.messages == ["This command is only for development environments"]

import pathlib
import poplib
from typing import List
from unittest.mock import create_autospec

import pytest

from mail import servers
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.icms import tasks
from mail.models import LicenceData, Mail, SourceEnum
from mail.utils import pop3


@pytest.fixture
def mock_pop3():
    """Mock pop3 to return a known response (CHIEF_licenceReply_29236_202209231140.eml)"""

    mock_pop3 = create_autospec(spec=poplib.POP3_SSL)

    # The return value of calling a magic mock is another instance of the mock with the same spec
    # mock = create_autospec(spec=SomeClass)
    # mock.return_value == mock()
    # Therefore we need to mock the methods on the return_value attribute
    # See here: https://docs.python.org/3/library/unittest.mock.html#calling
    mock_pop3.return_value.list.return_value = (b"+OK", [b"1 12345"], 1234)

    filename = "CHIEF_licenceReply_29236_202209231140.eml"
    mock_pop3.return_value.retr.return_value = (b"+OK", get_licence_reply_msg_list(filename), 1234)

    return mock_pop3


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

    expected_file = get_expected_file()

    actual_file = reply_file.get_payload(decode=True).decode()

    assert expected_file == actual_file


class TestProcessLicenceReplyAndUsageEmailTask:
    @pytest.fixture(autouse=True)
    def _setup(self, db, monkeypatch):
        self.con = None
        self.monkeypatch = monkeypatch

        # Create a mail object that is waiting for a licence reply from HMRC
        self.mail = Mail.objects.create(
            status=ReceptionStatusEnum.REPLY_PENDING,
            extract_type=ExtractTypeEnum.LICENCE_DATA,
            edi_filename="the_licence_data_file",
            edi_data="lovely data",
            sent_filename="the_licence_data_file",
            sent_data="lovely data",
        )
        LicenceData.objects.create(licence_ids="[88514]", hmrc_run_number=29236, source=SourceEnum.ICMS, mail=self.mail)

    def _patch_pop3_class(self, mock):
        # Store con reference to check what was called later
        self.con = mock.return_value

        # Patch where the pop3 connection is made
        self.monkeypatch.setattr(servers.poplib, "POP3_SSL", mock)

    def test_process_licence_reply_email_success(self, mock_pop3):
        self._patch_pop3_class(mock_pop3)

        # Check for emails and process them
        tasks.process_licence_reply_and_usage_emails()

        # Test the licence mail has been updated with the response email
        mail = LicenceData.objects.get(hmrc_run_number=29236).mail
        assert mail.status == ReceptionStatusEnum.REPLY_RECEIVED
        assert mail.response_filename == "CHIEF_licenceReply_29236_202209231140"
        assert mail.response_data == get_expected_file()

        # Successful processing should delete the message
        self.con.dele.assert_called_with("1")

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

    def test_process_licence_reply_errors_with_multiple_attachments(self, mock_pop3_multiple_attachments):
        self._patch_pop3_class(mock_pop3_multiple_attachments)

        # Only one attachment is accepted per licence reply email.
        with pytest.raises(ValueError, match="Only one attachment is accepted per licence reply email."):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

    def test_process_licence_reply_errors_with_unknown_email_subject(self, mock_pop3_unknown_subject):
        self._patch_pop3_class(mock_pop3_unknown_subject)

        with pytest.raises(ValueError, match="Unable to process email with subject: All about cakes"):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

    def test_process_licence_reply_errors_with_invalid_reply_subject(self, mock_pop3_invalid_reply_subject):
        self._patch_pop3_class(mock_pop3_invalid_reply_subject)

        with pytest.raises(
            ValueError, match="Unable to parse run number from 'CHIEF_licenceReply_INVALID_29236_202209231140'"
        ):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

    def test_process_usage_email_errors_until_implemented(self, mock_pop3_usage):
        self._patch_pop3_class(mock_pop3_usage)

        with pytest.raises(NotImplementedError):
            tasks.process_licence_reply_and_usage_emails()

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

        # Check any scheduled deletes were reset
        self.con.rset.assert_called_once()

    def test_process_email_usage_fake_success(self, mock_pop3_usage):
        self._patch_pop3_class(mock_pop3_usage)
        mock_save_usage = create_autospec(spec=tasks._save_usage_data_email)
        self.monkeypatch.setattr(tasks, "_save_usage_data_email", mock_save_usage)

        tasks.process_licence_reply_and_usage_emails()

        # Successful processing should delete the message
        self.con.dele.assert_called_with("1")

        # Check the connection was closed automatically
        self.con.quit.assert_called_once()

    def test_rollback_when_we_get_an_error_in_one_of_the_files(self, transactional_db):
        """Test a scenario where there is a good licence file and a bad usage file.

        Everything should roll back if we can't process everything.
        """

        mock_pop3_cls = create_autospec(spec=poplib.POP3_SSL)
        # Return multiple message id's (licenceReply and Usage)
        mock_pop3_cls.return_value.list.return_value = (b"+OK", [b"1 12345", b"2 54321"], 1234)

        def mock_retr(msg_id):
            if msg_id == "1":
                return b"+OK", get_licence_reply_msg_list("CHIEF_licenceReply_29236_202209231140.eml"), 12345

            if msg_id == "2":
                return b"+OK", get_licence_reply_msg_list("ILBDOTI_live_CHIEF_usageData_7132_202209280300.eml"), 54321

        mock_pop3_cls.return_value.retr = mock_retr
        self._patch_pop3_class(mock_pop3_cls)

        # Let's make the _save_usage_data_email fail with a custom error
        mock__save_usage_data_email = create_autospec(
            spec=tasks._save_usage_data_email, side_effect=RuntimeError("Something unexpected has happened...")
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
        assert self.mail.status == ReceptionStatusEnum.REPLY_PENDING
        assert not self.mail.response_filename
        assert not self.mail.response_data


# Note: Only added this test to cover a "partial" coverage line.
def test_get_run_number_from_unknown_subject():
    with pytest.raises(ValueError, match="Unable to parse run number from 'unknown_subject'"):
        tasks._get_run_number_from_subject("unknown_subject")


def get_licence_reply_msg_list(filename: str) -> List[bytes]:
    return pathlib.Path(f"mail/tests/files/icms/{filename}").read_bytes().split(b"\r\n")


def get_expected_file() -> str:
    filename = "mail/tests/files/icms/CHIEF_licenceReply_29236_202209231140_attachment"
    return pathlib.Path(filename).read_text()

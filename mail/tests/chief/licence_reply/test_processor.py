import pathlib

import pytest

from mail.chief.licence_reply import LicenceReplyProcessor
from mail.chief.licence_reply.types import FileError, RejectedTransactionError
from mail.enums import ExtractTypeEnum, MailStatusEnum
from mail.models import Mail


@pytest.fixture
def valid_licence_reply() -> str:
    filename = "mail/tests/files/icms/licence_reply/accepted_and_rejected_example"
    return pathlib.Path(filename).read_text()


@pytest.fixture
def partially_valid_licence_reply() -> str:
    filename = "mail/tests/files/icms/licence_reply/partially_valid_example"
    return pathlib.Path(filename).read_text()


@pytest.fixture
def valid_file_with_trailing_spaces() -> str:
    filename = "mail/tests/files/icms/licence_reply/accepted_with_trailing_spaces_example"
    return pathlib.Path(filename).read_text()


def test_processor_with_valid_file(valid_licence_reply):
    processor = LicenceReplyProcessor(valid_licence_reply)

    _assert_processor_valid(processor)


def test_processor_is_valid_with_mail_instance(valid_licence_reply):
    mail = Mail(
        id=1,
        response_subject="ExampleLicenceReply",
        response_data=valid_licence_reply,
    )

    # Test extract type error handling
    mail.extract_type = ExtractTypeEnum.USAGE_REPLY
    with pytest.raises(
        ValueError,
        match=r"Error with Mail \(1 - ExampleLicenceReply\): Invalid extract type usage_reply",
    ):
        LicenceReplyProcessor.load_from_mail(mail)
    mail.extract_type = ExtractTypeEnum.LICENCE_DATA

    # Test status error handling
    mail.status = MailStatusEnum.REPLY_PROCESSED

    with pytest.raises(
        ValueError,
        match=r"Error with Mail \(1 - ExampleLicenceReply\): Invalid status reply_processed",
    ):
        LicenceReplyProcessor.load_from_mail(mail)
    mail.status = MailStatusEnum.REPLY_RECEIVED

    # Finally check the file loaded correctly
    processor = LicenceReplyProcessor.load_from_mail(mail)
    _assert_processor_valid(processor)


def _assert_processor_valid(processor: LicenceReplyProcessor) -> None:
    assert processor.reply_file_is_valid()

    # Check accepted
    expected_accepted = ["ABC12345", "ABC12346", "ABC12348"]
    actual_accepted = [at.transaction_ref for at in processor.accepted_licences]
    assert expected_accepted == actual_accepted

    # Check rejected
    expected_rejected = ["ABC12347"]
    actual_rejected = [rt.header.transaction_ref for rt in processor.rejected_licences]
    assert expected_rejected == actual_rejected
    rejected_transaction = processor.rejected_licences[0]

    assert rejected_transaction.header.transaction_ref == "ABC12347"
    assert rejected_transaction.errors == [
        RejectedTransactionError(code="1234", text="Invalid thingy"),
        RejectedTransactionError(code="76543", text="Invalid commodity “1234A6” in line 23"),
    ]

    # Check trailer
    # header, trailer and two error lines
    assert int(rejected_transaction.end.record_count) == 4


def test_file_error():
    file_with_file_error = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\fileError\\18\\Record type 'fileHeader' not recognised\\99\n"
        "3\\fileTrailer\\0\\0\\1\n"
    )

    processor = LicenceReplyProcessor(file_with_file_error)

    assert processor.reply_file_is_invalid()
    expected_file_errors = [
        FileError(code="18", text="Record type 'fileHeader' not recognised", position="99")
    ]

    assert processor.file_errors == expected_file_errors

    assert int(processor.file_trailer.accepted_count) == 0
    assert int(processor.file_trailer.rejected_count) == 0
    assert int(processor.file_trailer.file_error_count) == 1


def test_rejected_error_out_of_order():
    # "error" line before a rejected line
    bad_file = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\error\\1234\\Invalid thingy\n"
        "3\\fileTrailer\\0\\1\\0"
        ""
    )

    with pytest.raises(
        ValueError, match="Unable to process file: rejected record is out of sequence on line 2"
    ):
        LicenceReplyProcessor(bad_file)


def test_rejected_end_out_of_order():
    # "end" line before a rejected line
    bad_file = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\end\\rejected\\4\n"
        "3\\fileTrailer\\0\\1\\0"
        ""
    )

    with pytest.raises(
        ValueError, match="Unable to process file: rejected record is out of sequence on line 2"
    ):
        LicenceReplyProcessor(bad_file)


def test_unknown_line_raises_error():
    # "end" line before a rejected line
    bad_file = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\unknown\\no idea\\\n"
        "3\\fileTrailer\\0\\0\\0"
        ""
    )

    with pytest.raises(ValueError, match="Unable to process file: Unknown field_type on line 2"):
        LicenceReplyProcessor(bad_file)


def test__check_can_process_is_called():
    processor = LicenceReplyProcessor("")

    with pytest.raises(
        ValueError,
        match="Unable to get accepted_licences when file isn't valid or partially valid.",
    ):
        _ = processor.accepted_licences

    with pytest.raises(
        ValueError,
        match="Unable to get rejected_licences when file isn't valid or partially valid.",
    ):
        _ = processor.rejected_licences


def test_processor_works_with_partially_valid_file(partially_valid_licence_reply):
    processor = LicenceReplyProcessor(partially_valid_licence_reply)

    assert not processor.reply_file_is_valid()
    assert not processor.reply_file_is_invalid()
    assert processor.reply_file_is_partially_valid()
    assert not processor.reply_file_contains_no_data()

    expected_accepted = ["ABC12345", "ABC12346"]
    actual_accepted = [at.transaction_ref for at in processor.accepted_licences]
    assert expected_accepted == actual_accepted
    assert not processor.rejected_licences

    expected_file_errors = [
        FileError(code="9", text="CHIEF server application error", position=None)
    ]
    assert processor.file_errors == expected_file_errors


def test_processor_works_with_reply_file_contains_no_data():
    processor = LicenceReplyProcessor("")

    assert not processor.reply_file_is_valid()
    assert not processor.reply_file_is_invalid()
    assert not processor.reply_file_is_partially_valid()
    assert processor.reply_file_contains_no_data()


def test_valid_file_with_trailing_spaces(valid_file_with_trailing_spaces):
    processor = LicenceReplyProcessor(valid_file_with_trailing_spaces)

    assert processor.reply_file_is_valid()

    expected_references = ["IMA/2024/00558"]
    actual_references = [at.transaction_ref for at in processor.accepted_licences]

    assert expected_references == actual_references


def test_valid_file_with_trailing_spaces_with_mail_instance(valid_file_with_trailing_spaces):
    mail = Mail(
        id=1,
        response_subject="ExampleLicenceReply",
        response_data=valid_file_with_trailing_spaces,
        extract_type=ExtractTypeEnum.LICENCE_DATA,
        status=MailStatusEnum.REPLY_RECEIVED,
    )

    processor = LicenceReplyProcessor.load_from_mail(mail)
    assert processor.reply_file_is_valid()

    expected_references = ["IMA/2024/00558"]
    actual_references = [at.transaction_ref for at in processor.accepted_licences]

    assert expected_references == actual_references

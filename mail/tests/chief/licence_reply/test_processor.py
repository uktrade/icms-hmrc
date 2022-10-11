import pathlib

import pytest

from mail.chief.licence_reply import LicenceReplyProcessor
from mail.chief.licence_reply.types import FileError, RejectedTransactionError
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.models import Mail


@pytest.fixture
def licence_reply_example() -> str:
    filename = "mail/tests/files/icms/CHIEF_licenceReply_accepted_and_rejected_example"
    return pathlib.Path(filename).read_text()


def test_processor_with_valid_file(licence_reply_example):
    processor = LicenceReplyProcessor(licence_reply_example)

    _assert_processor_valid(processor)


def test_processor_is_valid_with_mail_instance(licence_reply_example):
    mail = Mail(
        id=1,
        response_subject="ExampleLicenceReply",
        response_data=licence_reply_example,
    )

    # Test extract type error handling
    mail.extract_type = ExtractTypeEnum.USAGE_REPLY
    with pytest.raises(
        ValueError, match=r"Error with Mail \(1 - ExampleLicenceReply\): Invalid extract type usage_reply"
    ):
        LicenceReplyProcessor.load_from_mail(mail)
    mail.extract_type = ExtractTypeEnum.LICENCE_DATA

    # Test status error handling
    mail.status = ReceptionStatusEnum.REPLY_SENT

    with pytest.raises(ValueError, match=r"Error with Mail \(1 - ExampleLicenceReply\): Invalid status reply_sent"):
        LicenceReplyProcessor.load_from_mail(mail)
    mail.status = ReceptionStatusEnum.REPLY_RECEIVED

    # Finally check the file loaded correctly
    processor = LicenceReplyProcessor.load_from_mail(mail)
    _assert_processor_valid(processor)


def _assert_processor_valid(processor: LicenceReplyProcessor) -> None:
    assert processor.file_valid()

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

    assert not processor.file_valid()
    expected_file_errors = [FileError(code="18", text="Record type 'fileHeader' not recognised", position="99")]

    assert processor.file_errors == expected_file_errors


def test_rejected_error_out_of_order():
    # "error" line before a rejected line
    bad_file = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\error\\1234\\Invalid thingy\n"
        "3\\fileTrailer\\0\\1\\0"
        ""
    )

    with pytest.raises(ValueError, match="Unable to process file: rejected record is out of sequence on line 2"):
        LicenceReplyProcessor(bad_file)


def test_rejected_end_out_of_order():
    # "end" line before a rejected line
    bad_file = (
        "1\\fileHeader\\CHIEF\\ILBDOTI\\licenceReply\\202209231140\\29236\n"
        "2\\end\\rejected\\4\n"
        "3\\fileTrailer\\0\\1\\0"
        ""
    )

    with pytest.raises(ValueError, match="Unable to process file: rejected record is out of sequence on line 2"):
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


def test_is_valid_is_called():
    processor = LicenceReplyProcessor("")

    with pytest.raises(
        ValueError, match="Unable to get accepted_licences when file hasn't been validated or is invalid"
    ):
        _ = processor.accepted_licences

    with pytest.raises(
        ValueError, match="Unable to get rejected_licences when file hasn't been validated or is invalid"
    ):
        _ = processor.rejected_licences

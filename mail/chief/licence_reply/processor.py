from dataclasses import dataclass, field
from typing import Any, List, Optional

from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.libraries import chiefprotocol
from mail.models import Mail

from .types import (
    AcceptedTransaction,
    FileError,
    FileHeader,
    FileTrailer,
    RejectedTransactionError,
    RejectedTransactionHeader,
    RejectedTransactionTrailer,
)


@dataclass()
class RejectedTransaction:
    """This isn't a chief type but represents all attributes of a rejected transaction."""

    header: RejectedTransactionHeader
    errors: List[RejectedTransactionError] = field(default_factory=list)
    end: RejectedTransactionTrailer = None


class LicenceReplyProcessor:
    LINE_MAP = {
        FileHeader.record_type: FileHeader,
        FileError.record_type: FileError,
        AcceptedTransaction.record_type: AcceptedTransaction,
        RejectedTransactionHeader.record_type: RejectedTransactionHeader,
        RejectedTransactionError.record_type: RejectedTransactionError,
        RejectedTransactionTrailer.record_type: RejectedTransactionTrailer,
        FileTrailer.record_type: FileTrailer,
    }

    def __init__(self, data: str) -> None:
        self._valid = False

        # File attributes
        self.file_header: Optional[FileHeader] = None
        self.file_errors: List[FileError] = []
        self.file_trailer: Optional[FileTrailer] = None

        # Licence attributes
        self._accepted: List[AcceptedTransaction] = []
        self._rejected: List[RejectedTransaction] = []

        # Used when iterating over rejected applications
        self._current_rejected = None

        self._load_licence_reply_data(data)

    @classmethod
    def load_from_mail(cls, mail: Mail) -> "LicenceReplyProcessor":
        if mail.extract_type != ExtractTypeEnum.LICENCE_DATA:
            raise ValueError(
                f"Error with Mail ({mail.id} - {mail.response_subject}): Invalid extract type {mail.extract_type}"
            )

        if mail.status != ReceptionStatusEnum.REPLY_RECEIVED:
            raise ValueError(f"Error with Mail ({mail.id} - {mail.response_subject}): Invalid status {mail.status}")

        return cls(mail.response_data)

    @property
    def accepted_licences(self) -> List[AcceptedTransaction]:
        self._check_is_valid("accepted_licences")

        return self._accepted

    @property
    def rejected_licences(self) -> List[RejectedTransaction]:
        self._check_is_valid("rejected_licences")

        return self._rejected

    def _load_licence_reply_data(self, reply_data: str) -> None:
        """Load the licence reply data."""

        for line in filter(None, reply_data.split(chiefprotocol.LINE_SEP)):
            self._process_line(line)

    def _process_line(self, line: str) -> None:
        """Process the reply data line into the correct chief type."""

        line_no: int
        field_type: str
        record_args: List[Any]
        line_no, field_type, *record_args = line.split(chiefprotocol.FIELD_SEP)

        try:
            record = self.LINE_MAP[field_type](*record_args)
        except KeyError:
            raise ValueError(f"Unable to process file: Unknown field_type on line {line_no}")

        if field_type == FileHeader.record_type:
            self.file_header = record

        elif field_type == FileError.record_type:
            self.file_errors.append(record)

        elif field_type == AcceptedTransaction.record_type:
            self._accepted.append(record)

        elif field_type == RejectedTransactionHeader.record_type:
            # Create a new current rejected value (rejected transaction spans multiple lines)
            self._current_rejected = RejectedTransaction(header=record)

        elif field_type == RejectedTransactionError.record_type:
            if not self._current_rejected:
                raise ValueError(f"Unable to process file: rejected record is out of sequence on line {line_no}")
            self._current_rejected.errors.append(record)

        elif field_type == RejectedTransactionTrailer.record_type:
            if not self._current_rejected:
                raise ValueError(f"Unable to process file: rejected record is out of sequence on line {line_no}")

            self._current_rejected.end = record

            # Add the complete current rejected to the list of rejected transactions
            self._rejected.append(self._current_rejected)

            # Reset current rejected
            self._current_rejected = None

        elif field_type == FileTrailer.record_type:  # pragma: no cover
            self.file_trailer = record

    def file_valid(self) -> bool:
        self._valid = not self.file_errors and self.file_trailer_valid()

        return self._valid

    def file_trailer_valid(self) -> bool:
        accepted_match = len(self._accepted) == int(self.file_trailer.accepted_count)
        rejected_match = len(self._rejected) == int(self.file_trailer.rejected_count)

        return accepted_match and rejected_match

    def _check_is_valid(self, action) -> None:
        if not self._valid:
            raise ValueError(f"Unable to get {action} when file hasn't been validated or is invalid")

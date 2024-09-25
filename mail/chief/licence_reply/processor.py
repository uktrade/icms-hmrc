from dataclasses import dataclass, field
from typing import Any, List, Optional

from mail.chief import FIELD_SEP, LINE_SEP
from mail.enums import ExtractTypeEnum, MailStatusEnum
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

"""
The following has been taken from DES23513 - TIS LINE FILE DIALOGUE AND SYNTAX and is included here
to help anyone trying to understand the logic in the following methods:
    LicenceReplyProcessor.reply_file_is_valid
    LicenceReplyProcessor.reply_file_is_invalid
    LicenceReplyProcessor.reply_file_is_partially_valid
    LicenceReplyProcessor.reply_file_contains_no_data

The reply file contains the response data for a particular input file.
The reply file may reject the whole of the input file or contain an acceptance or rejection
message for each transaction in the input file that has been processed and at least one file
level error if some transactions may not have been processed.

Taken the above to work out the following outcomes:
1. The Reply file is valid and each transaction is either accepted or rejected
2. The Reply file is completely invalid and contains only file errors
3. The Reply file contains accepted / rejected transactions and one or more file errors.
   This indicates that it didn't process every licence we sent to CHIEF.

====================================================================================================
Error Processing
====================================================================================================

1. An input file may be processed in one or two passes:
    A) Two Pass File Handling.
        The first pass verifies that controlling information is correct (e.g. in sequence),
        and that the file is logically complete and structurally sound, and the second pass
        processes the transactions on the file. If any errors are found during the first pass,
        the second pass is not performed. First pass errors include identifying unrecognised record
        types, records out of sequence, incomplete transactions. The depth of checking in the
        first pass could mean that the second pass would always be able to process all the
        transactions in the file but this should not be assumed. File level error codes are
        suggested in Section 5.2.1 (other values may be defined for an interface).

    B) One Pass File Handling.
        For processing in a single pass, file corruption may be encountered after processing some of
        the transactions (e.g. file trailer missing) so some transactions in the file may not be
        recognised and will not be explicitly identified in the reply file. Once a file error is
        encountered further transactions need not be processed but this should not be assumed when
        processing the reply file.

This means that the reply file contains one of the following:
    - One or more file errors that mean that it was not safe to process any of the transactions;
    - A response for each transaction in the file;
    - A response for each transaction that was processed and one or more file errors.

2. If the file is so damaged that key attributes (e.g. the run number) cannot be determined so it is
   not considered safe to generate a reply file, then the file must be quarantined and the recipient
   is responsible for contacting the sender’s designated interface administrator to instigate
   recovery action.

3. If the server application fails then a file may be returned with the results of any transactions
   processed before the failure. A file error (see 5.2.1 code “9”) should be appended with no
   following file trailer. Manual recovery will be required to check which transactions have been
   processed and to resubmit transactions that have not been processed.

4. The originating organisation is expected to investigate if a reply file is not received within
   the expected time period. For sequential processing the file can be sent again since it will be
   rejected if it has been processed (not the expected run number). For parallel processing the
   file can only be resent if the transactions can be reprocessed without harm.

====================================================================================================
Error Recovery
====================================================================================================

The interface is being used to transfer data between tested systems with the client system applying
agreed validation rules to ensure data is acceptable to the server system. Transactions should be
accepted by the server system for investigation when exceptions are detected by the server
application that could result from reference data being inconsistent with that held on the client
system or are found in input data that is not validated by the client system.

If problems occur then recovery will have to be within the current capabilities of the systems and
action should be taken to ensure the problem does not happen again. The following features may
help with error recovery:
    1. The receiving party can request that an input file or reply file be completely
       re-transmitted. If a file is garbled during transmission, the file should be resent rather
       than re-built using a new run number.
    2. For sequential processing the criteria for the recipient to update the expected run number
       could limit the options for recovery when some transactions have been accepted. However the
       file header includes an optional attribute to reset the run number. This means that a file
       can be edited to correct data and sent with a run number that corrects the sequence for the
       next file that may already have been extracted.
    3. Where possible the processing system should enable accepted transactions to be sent again.
       The effect should be defined for the interface so suitable recovery action can be taken.
    4. Where possible erroneous data should be corrected in the client system and extracted for a
       subsequent run.
    5. In some circumstances it may be possible for the originating organisation to request that a
       file be ignored so that a new file can be transmitted using the same run number. This will
       only be possible if the file has not been processed or any changes can be rolled back.
       This is unlikely to be possible for any data sent to CHIEF as processing will not be delayed
       and changes will have been committed to the CHIEF database.
       The circumstances under which rollback is a possible recovery action should be identified in
       the Interchange Agreement.
"""


@dataclass()
class RejectedTransaction:
    """This isn't a chief type but represents all attributes of a rejected transaction."""

    header: RejectedTransactionHeader
    errors: List[RejectedTransactionError] = field(default_factory=list)
    end: RejectedTransactionTrailer = None


class LicenceReplyProcessor:
    """Class that processes licence reply data."""

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
        self._can_process = False

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

        if mail.status not in [
            MailStatusEnum.REPLY_RECEIVED,
            MailStatusEnum.REPLY_PARTIALLY_PROCESSED,
        ]:
            raise ValueError(
                f"Error with Mail ({mail.id} - {mail.response_subject}): Invalid status {mail.status}"
            )

        return cls(mail.response_data)

    def reply_file_is_valid(self):
        """The Reply file is valid and each transaction is either accepted or rejected"""

        # The file trailer can be missing
        if not self.file_trailer:
            return False

        no_file_errors = not self.file_errors and int(self.file_trailer.file_error_count) == 0
        accepted_match = len(self._accepted) == int(self.file_trailer.accepted_count)
        rejected_match = len(self._rejected) == int(self.file_trailer.rejected_count)

        is_valid = accepted_match and rejected_match and no_file_errors

        if is_valid:
            self._can_process = True

        return is_valid

    def reply_file_is_invalid(self):
        """The Reply file is completely invalid and contains only file errors"""

        return self.file_errors and not self._accepted and not self._rejected

    def reply_file_is_partially_valid(self):
        """The Reply file contains accepted / rejected transactions and one or more file errors.

        This indicates that it didn't process every licence we sent to CHIEF.
        """

        partially_valid = self.file_errors and (self._accepted or self._rejected)

        if partially_valid:
            self._can_process = True

        return partially_valid

    def reply_file_contains_no_data(self):
        """Edge case where there are no file errors, accepted or rejected transactions."""

        return not self.file_errors and not self._accepted and not self._rejected

    @property
    def accepted_licences(self) -> List[AcceptedTransaction]:
        self._check_can_process("accepted_licences")

        return self._accepted

    @property
    def rejected_licences(self) -> List[RejectedTransaction]:
        self._check_can_process("rejected_licences")

        return self._rejected

    def _load_licence_reply_data(self, reply_data: str) -> None:
        """Load the licence reply data."""

        for line in filter(None, reply_data.split(LINE_SEP)):
            # The live licenceReply file contains empty spaces at the end of each line.
            stripped = line.rstrip()
            self._process_line(stripped)

    def _process_line(self, line: str) -> None:
        """Process the reply data line into the correct chief type."""

        line_no: int
        field_type: str
        record_args: List[Any]
        line_no, field_type, *record_args = line.split(FIELD_SEP)

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
                raise ValueError(
                    f"Unable to process file: rejected record is out of sequence on line {line_no}"
                )
            self._current_rejected.errors.append(record)

        elif field_type == RejectedTransactionTrailer.record_type:
            if not self._current_rejected:
                raise ValueError(
                    f"Unable to process file: rejected record is out of sequence on line {line_no}"
                )

            self._current_rejected.end = record

            # Add the complete current rejected to the list of rejected transactions
            self._rejected.append(self._current_rejected)

            # Reset current rejected
            self._current_rejected = None

        elif field_type == FileTrailer.record_type:  # pragma: no cover
            self.file_trailer = record

    def file_trailer_valid(self) -> bool:
        accepted_match = len(self._accepted) == int(self.file_trailer.accepted_count)
        rejected_match = len(self._rejected) == int(self.file_trailer.rejected_count)

        return accepted_match and rejected_match

    def _check_can_process(self, action) -> None:
        if not self._can_process:
            raise ValueError(f"Unable to get {action} when file isn't valid or partially valid.")

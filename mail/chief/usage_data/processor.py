from typing import Any

from mail.chief import FIELD_SEP, LINE_SEP
from mail.enums import ExtractTypeEnum, MailStatusEnum
from mail.models import Mail

from .types import (
    EndLine,
    FileHeader,
    FileTrailer,
    LicenceLine,
    LicenceUsage,
    LicenceUsageTransactionHeader,
    LineUsageTransactionTrailer,
)


class UsageDataProcessor:
    def __init__(self, data: str) -> None:
        self._valid = False

        # File attributes
        self.file_header: FileHeader | None = None
        self.file_trailer: FileTrailer | None = None
        self._usages: list[LicenceUsageTransactionHeader] = []

        self._load_usage_data(data)

    @classmethod
    def load_from_mail(cls, mail: Mail) -> "UsageDataProcessor":
        if mail.extract_type != ExtractTypeEnum.USAGE_DATA:
            raise ValueError(
                f"Error with Mail ({mail.id} - {mail.response_subject}): Invalid extract type {mail.extract_type}"
            )

        if mail.status != MailStatusEnum.REPLY_RECEIVED:
            raise ValueError(
                f"Error with Mail ({mail.id} - {mail.response_subject}): Invalid status {mail.status}"
            )

        return cls(mail.response_data)

    @property
    def usage_licences(self) -> list[dict[str, str]]:
        if not self._valid:
            raise ValueError(
                "Unable to get usage_licences when file hasn't been validated or is invalid"
            )

        return [
            {"licence_ref": u.licence_ref, "licence_status": u.licence_status} for u in self._usages
        ]

    def _load_usage_data(self, usage_data: str) -> None:
        """Load the usage data."""

        for line in filter(None, usage_data.split(LINE_SEP)):
            self._process_line(line)

    def _process_line(self, line: str) -> None:
        """Process the usage data line into the correct chief type.

        Note: We do not currently care about the following types:
            - LicenceLine
            - LicenceUsage
            - EndLine
            - LineUsageTransactionTrailer
        """

        line_no: int
        field_type: str
        record_args: list[Any]
        line_no, field_type, *record_args = line.split(FIELD_SEP)

        match field_type:
            case FileHeader.record_type:
                self.file_header = FileHeader(*record_args)
            case LicenceUsageTransactionHeader.record_type:
                self._usages.append(LicenceUsageTransactionHeader(*record_args))
            case LicenceLine.record_type:
                pass
            case LicenceUsage.record_type:
                pass
            case EndLine.record_type | LineUsageTransactionTrailer.record_type:
                # Just documenting the fact that the record type is the same for both so
                # the start_record_type must be used to differentiate the row.
                start_record_type = record_args[0]

                if start_record_type == "line":
                    pass
                elif start_record_type == "licenceUsage":
                    pass
                else:
                    raise ValueError(
                        f"Unable to process file: Unknown start record type ({start_record_type}) on line {line_no}"
                    )
            case FileTrailer.record_type:
                self.file_trailer = FileTrailer(*record_args)
            case _:
                raise ValueError(
                    f"Unable to process file: Unknown field_type ({field_type}) on line {line_no}"
                )

    def file_valid(self) -> bool:
        self._valid = self.file_trailer_valid()

        return self._valid

    def file_trailer_valid(self) -> bool:
        return len(self._usages) == int(self.file_trailer.transaction_count)

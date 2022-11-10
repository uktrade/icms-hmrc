from dataclasses import dataclass
from typing import ClassVar

"""
---------------------
Generic Record Structure
---------------------
Attribute       Format      Presence    Comments
recordSeqNum    9(7)        M           Records are numbered sequentially from 1 for the file header through to the file trailer.
recordType      a(..35)     M


The definition does not include recordSeqNum that is transferred as the first field of the record.
The recordType is transferred as the second field (see Section 3.3.1).
The recordType and Attributes are identified by potential XML tag names (lower Camel case, e.g. startDate).

Character attribute formats are defined as: <type><length>
where <type> is:
        a    alphabetic characters
        A    upper case alphabetic characters
        N    numeric characters
        aN    alphanumeric characters
        AN    upper case alphabetic and numeric characters
        X    text (any permitted character, see Section 3.2)
        T    formatted text (includes ‘|’)
and <length> is:
        (n)    fixed length of n characters
        (..n)    variable length of up to n characters

Numeric attribute formats are defined as:
        9(n)    integer field of length up to n digits
        9(n).9(m)    decimal field with up to n digits before the decimal point and up to m digits after.

The presence of an attribute is defined by the following values:
        A    Absent for this transaction type/action.
        C    Conditional on the presence or absence or value of other data sent for the transaction
        M    Mandatory.
        O    Optional.
The optional attributes may not be relevant to some systems.
The use of attributes can be clarified in the Interchange Agreement.
For some attributes CHIEF can be configured on a per-system basis to check that they are not used or that their use is
restricted to particular values.
All literal values in the record specifications are enclosed in double quotes and are case sensitive (e.g. “insert”).

---------------------
Reply file definition
---------------------
The reply file has a common definition for all interfaces.
A reply file consists of a file header and a file trailer record encapsulating transaction responses and/or file errors.
The reply file structure is:

Level       Record                          Presence        Notes
1           File Header                     M               same run number as the related input file.
    2       Accepted Transaction            C               for each accepted transaction
    2       Rejected Transaction Header     C               for each rejected transaction
        3   Error                           C               at least one error
    2       Rejected Transaction Trailer    C               for each rejected transaction
    2       File Error                      C               for each error detected
1           File Trailer                    M               completion check
"""


@dataclass
class FileHeader:
    """The reply file header.

    Attribute           Format      Presence    Comments
    sourceSystem        A(..8)      M           The server system that generates the reply file.
    destinationSystem   A(..8)      M           The client system that generated the input file and to which the reply file is sent.
    dataId              a(..17)     M           Identifier for the transaction data that is in the reply file as defined for the interface.
    creationDateTime    N(12)       M           Date-time of creation of the reply file (format ccyymmddhhmm).
    runNum              9(7)        M           The run number from the input file.
    """

    record_type: ClassVar[str] = "fileHeader"

    source_system: str
    destination: str
    data_id: str
    creation_datetime: str
    run_num: int


@dataclass
class FileError:
    """The file error record identifies an error in the overall structure of the input file or a run sequence error.

    Attribute       Format      Presence    Comments
    code            AN(..6)     M           See Section 5.2.1 for recommended error codes and text.
    text            X(..130)    M           See Section 5.2.1 for recommended error codes and text.
    position        9(7)        O           Sequence number of the record on the input file at which the error is detected.
                                            If supplied for a record out of sequence it is the expected number.
    """

    record_type: ClassVar[str] = "fileError"

    code: str
    text: str
    position: str


@dataclass
class AcceptedTransaction:
    """The accepted transaction record is returned when the input transaction is accepted and has been full processed.

    Attribute       Format      Presence    Comments
    transactionRef  X(..17)     M           As given for the transaction on the input file.
    """

    record_type: ClassVar[str] = "accepted"

    transaction_ref: str


@dataclass
class RejectedTransactionHeader:
    """The rejected transaction structure is used when the input transaction is rejected.

    The structure allows one or more errors to be identified.

    Attribute       Format      Presence    Comments
    transactionRef  X(..17)     M           As given for the transaction on the input file.
    """

    record_type: ClassVar[str] = "rejected"

    transaction_ref: str


@dataclass
class RejectedTransactionError:
    """A transaction error record identifies an error in the transaction data.

    Attribute       Format      Presence    Comments
    code            AN(..6)     M           As defined for the interface.
    text            X(..130)    M           The error text should identify the position of the error or the erroneous
                                            data (e.g. “invalid commodity on line 17”)
    """

    record_type: ClassVar[str] = "error"

    code: str
    text: str


@dataclass
class RejectedTransactionTrailer:
    """Trailer record for rejected transaction.

    Attribute       Format      Presence    Comments
    startRecordType a(8)        M           “rejected”
    recordCount     9(5)        M           Count of records containing transaction data including the header
                                            and this trailer record.
    """

    record_type: ClassVar[str] = "end"

    start_record_type: str
    record_count: int


@dataclass
class FileTrailer:
    """Signifies end of the file.

    It must be in sequence and the last record in the file.
    This record may be missing following a server application failure.

    Attribute       Format      Presence    Comments
    acceptedCount   9(5)        M           Can be zero.
    rejectedCount   9(5)        M           Can be zero.
    fileErrorCount  9(5)        M           Can be zero.
    """

    record_type: ClassVar[str] = "fileTrailer"

    accepted_count: int
    rejected_count: int
    file_error_count: int

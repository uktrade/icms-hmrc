from dataclasses import dataclass
from typing import ClassVar, Literal

"""
The input and reply file identifiers for the filenames and header records are:

Input file: “usageData”
Reply file: “usageReply”

ICMS only receives the usageData file it does not send back a reply file.

Usage details are extracted on a daily basis and an empty file (i.e. a file containing no transactions – just the file header and trailer records) is sent if there is no usage to report.
Licence usage files are processed sequentially.
CHIEF does not send another input file to an OGD until a reply file has been received and checked.
If any errors are reported they have to be corrected manually – usage details cannot be extracted again for particular licences from CHIEF.
As far as the CHIEF is concerned once the extract transaction completes the extracted file is committed along with database changes including incrementing the run number for the next extract for a particular OGD.
Once the interface with an OGD system has been tested there should not be any errors detected.
CHIEF can send the file again if necessary.
In the extreme it might be necessary to send an empty file to update the expected run number in the receiving OGD system.
The run number is reset to zero following 99999 (i.e. after 270 or so years at one file per day).

---------------------
Input File Processing
---------------------
OGDs process a batch of transaction requests in the input file which was sent by CHIEF in the structure defined in TIS: Line File Dialogue and Syntax.
CHIEF sends null trailing fields in all records on the input file except for the file trailer record.
The OGD system must only increment the expected run number if all licence usage transactions are reported as accepted on the reply file and no file errors are detected.


---------------------
Usage Data file definition
---------------------


Level       Record                              Presence    Occurs      Notes
1           Licence Usage Transaction Header    M
  2         Line                                M           1000        For each licence line
    3       Usage                               O           100         As required for the licence type
  2         End Line                            M           Per line    for each licence line
1           Licence Usage Transaction Trailer   M
"""


@dataclass
class FileHeader:
    """The usage data file header.

    Attribute           Format      Presence    Comments
    sourceSystem        AN(..8)     M           The client system that generates the input file.
                                                The first 4 characters uniquely identify the system.
    destinationSystem   AN(..8)     M           The server system that is to process the input transactions.
    dataId              a(..17)     M           Identifier for the transaction data that is in the input file as defined for the interface.
    creationDateTime    N(12)       M           Date-time of creation of the input file (format ccyymmddhhmm).
    runNum              9(7)        M           For sequential processing the run number must be 1 on the first transmission and then incremented (by one) on each subsequent transmission.
                                                A run number is not expected to cycle but if it can for an interface it should roll to zero.
                                                An interface can define any special ways in which run numbers are handled.
                                                For parallel processing the run number should follow the same rules and must be unique for the period for which data may be retained by either system.
                                                Sequence checking by the processing system is overridden by setting resetRunNum to “Y”.
    resetRunNum         A(1)        O           If “Y” the given runNum overrides the value expected by the processing system.
                                                For sequential processing, the next file sent should have the next number.
                                                For parallel processing it must be set to “Y”.
    """

    record_type: ClassVar[str] = "fileHeader"

    source_system: str
    destination: str
    data_id: str
    creation_datetime: str
    run_num: int
    reset_run_num: int | None = None


@dataclass
class LicenceUsageTransactionHeader:
    """The licence usage transaction header.

    Attribute           Format      Presence    Comments
    transactionRef      X(17)       M           Identifies the transaction uniquely as follows: LU<run number>/<transaction sequence number> Returned in the transaction response record.
    action              a(6)        M           “insert” only
    licenceRef          X(..35)     M           Licence Reference as advised when the licence was inserted on CHIEF.
    licenceStatus       A           M           The current status of the licence:
                                                    “C” Cancelled
                                                    “E” Exhaustion Notified
                                                    “O” Open
                                                    “S” Surrender Notified (RPA only)
                                                    “D” Date expired
                                                Any of the values may be sent in a transaction returning daily usage details to the issuing authority.
                                                The completionDate is not returned for a daily usage transaction.
    completionDate     N(8)         C           Only sent when the licence is complete on CHIEF and there is no more usage to report (i.e. status is not “O”, no usage is pending and the delay period following date expiry has been exceeded).
                                                The completion date, in format ccyymmdd, for the licence is the later of dates on which:
                                                    - The status was advised (“C”,”E”,”S”) or occurred (“D”);
                                                    - The last consignment with pending attribution was departed (exports) or cleared (imports).
                                                    - The delay period following date expiry is exceeded (the delay period is defined for a licence type to allow the licence to be used by Supplementary Declarations).
    """

    record_type: ClassVar[str] = "licenceUsage"

    transaction_ref: str
    action: Literal["insert"]
    licence_ref: str
    licence_status: str
    completion_date: str | None = None


@dataclass
class LicenceLine:
    """For a single line licence usage is returned for line 1 (i.e. usage is not separately supplied for the commodities that may optionally be identified in additional lines).
    When usage details are being reported, the current totals include any previously reported usage and the usage reported in the subordinate records in this transaction.

    Attribute           Format      Presence    Comments
    lineNum             9(5)        M           Line number as recorded on the Licence Line when originally notified to CHIEF.
    quantityUsed        9(11).9(3)  C           Current total used if controlled by quantity (otherwise zero or null may be sent).
    valueUsed           9(10).99    C           Current total used if controlled by value (otherwise zero or null may be sent).
    currency            A(3)        C           If controlled by value.
    """

    record_type: ClassVar[str] = "line"

    line_num: int
    quantity_used: float | None = None
    value_used: float | None = None
    currency: str | None = None


@dataclass
class LicenceUsage:
    """Usage records are included when the transaction is being used to report daily usage.
    There will not be any usage records when the transaction is reporting licence completion (see LicenceUsageTransactionHeader.completionDate).
    If the licence completes at the same time as the final usage details are reported then the file will contain two transactions for the same licence – usage details followed by completion details.

    Attribute           Format      Presence    Comments
    usageType           A(1)        M           Types are:
                                                    “A” Adjusted by Customs;
                                                    “C” Contra by Customs;
                                                    “L” Late original (adjustment by Customs);
                                                    “M” Additional MIC and Message only;
                                                    "O” Original attribution.
    declarationUCR      X(..35)     M
    declarationPartNum  X(..4)      M
    controlDate         N(8)        M           Date into control (arrival at Office of Export/Import), in format ccyymmdd.
    quantityUsed        9(11).9(3)  C           Given if the licence is controlled by quantity (otherwise zero or null may be sent).
                                                The amount is the corrected attribution for an adjustment (claimType “A”) and is zero for a contra (claimType “C”).
    valueUsed           9(10).99    C           Given if the licence is controlled by value (otherwise zero or null may be sent).
                                                The amount is the corrected attribution for an adjustment (claimType “A”) and is zero for a contra (claimType “C”).
    currency            A(3)        C           Given if the licence is controlled by value.
    traderId            X(..12)     C           RPA Registered Trader Number if declared else Importer/Exporter TURN except for a late original adjustment when the information may no longer be available.
    claimRef            N(8)        C           CAP Exports refund claim only.
                                                It should be noted that the usage may be the sum of the usage for more than one item (claim line).
                                                The claimRef will be reported for the use of any licence on a CAP refund claim except for a late original adjustment when the information may no longer be available.
    originCountry       A(2)        C           Imports only.
                                                Usage is accumulated and reported for the entry.
                                                The country is as declared for the first item that uses the licence.
                                                Other items may be declared with different countries of origin.
                                                For a late original adjustment the information may no longer be available.
    customsMIC          AN(4)       C           Occurs for an “O” usageType when the licence has an associated Customs Check requiring a MIC.
                                                MICs are defined for particular licence types with the fourth character identifying a specific check.
                                                There may be an additional “M” usageType record when the licence usage is aggregated from more than one item on the declaration.
    customsMessage      X(..20)     C           Occurs with customsMIC when the MIC is defined to require a textual message.

    consigneeName       X(35)       C           Consignee Name from Header (or Item if bulk Entry).
                                                Optional field present only on ‘Usage’s sent to RPA.
                                                consigneeName is only populated for RPA CAP Import Licences (Licence Type = ‘CPI’).
    """

    record_type: ClassVar[str] = "usage"

    usage_type: str
    declaration_ucr: str
    declaration_part_num: str
    control_date: str
    quantity_used: float | None = None
    value_used: float | None = None
    currency: str | None = None
    trader_id: str | None = None
    claim_ref: int | None = None
    origin_country: str | None = None
    customs_mic: str | None = None
    customs_message: str | None = None
    consignee_name: str | None = None


@dataclass
class EndLine:
    """EndLine for each LicenceLine.

    Attribute           Format      Presence    Comments
    startRecordType     a(4)        M           “line”
    recordCount         9(5)        M           Count of records containing line data including the “line” and “end” records (i.e. ‘2’ if there are no usage records).
    """

    record_type: ClassVar[str] = "end"

    start_record_type: str
    record_count: int


@dataclass
class LineUsageTransactionTrailer:
    """Licence usage transaction trailer line.

    Attribute           Format      Presence    Comments
    startRecordType     a(12)       M           “licenceUsage”
    recordCount         9(5)        O           Count of records containing transaction data including the transaction header and this end record.
                                                The count includes records at all levels in the transaction structure.
    """

    record_type: ClassVar[str] = "end"

    start_record_type: str
    record_count: int | None = None


@dataclass
class FileTrailer:
    """File Trailer record.

    Attribute           Format      Presence    Comments
    transactionCount    9(5)        O           Count of the transactions on the input file.
                                                The count is checked by the recipient (or a gateway en route) if supplied.
    hashTotal           9(11).9(3)  O           Hash total of quantity attributes in the transaction records modulo 100,000,000,000.
                                                Use of this attribute is defined in the interface document for those interfaces where it is required.
    """

    record_type: ClassVar[str] = "fileTrailer"

    transaction_count: int | None = None
    hash_total: float | None = None

from dataclasses import dataclass
from typing import Optional

# These types represent the structure of records in a CHIEF message. A message
# is one of licenceData, licenceReply, usageData, or usageReply types.


# Every line in a message starts with a line number, and then the record type.
@dataclass
class _Record:
    lineno: Optional[int] = None
    type_: Optional[str] = None


# Every message starts and ends with the file header.
@dataclass
class FileHeader(_Record):
    type_: Optional[str] = "fileHeader"

    # System that generates the input file. Required.
    source_system: Optional[str] = None

    # System that processes the input transactions. Required.
    destination_system: Optional[str] = None
    data_id: Optional[str] = None

    # Date-time of creation of the input file, format ccyymmddhhmm.
    creation_date_time: Optional[str] = None

    # The run number must be 1 on the first transmission and then incremented
    # (by one) on each subsequent transmission. A run number is not expected to
    # cycle but if it can for an interface it should roll to zero.
    run_num: Optional[int] = None

    # For ICMS this is usually (always?) "N". If "Y" the given runNum
    # overrides the value expected by the processing system. For sequential
    # processing, the next file sent should have the next number. For parallel
    # processing it must be set to "Y".
    reset_run_num: Optional[str] = None


@dataclass
class FileTrailer(_Record):
    type_: Optional[str] = "fileTrailer"
    transaction_count: Optional[int] = None
    # The spec also allows a hash_total field, but this implementation
    # flags that as an error when validating.
    # hash_total: Optional[str] = None


# Several types have a matching "end" line.
@dataclass
class End(_Record):
    type_: Optional[str] = "end"
    start_record_type: Optional[str] = None
    record_count: Optional[int] = None


# Licence data (request).
@dataclass
class Licence(_Record):
    type_: Optional[str] = "licence"

    # Required for insert, replace, cancel.
    transaction_ref: Optional[str] = None

    # Required for insert, replace, cancel.
    action: Optional[str] = None

    # Required for insert, replace, cancel.
    licence_ref: Optional[str] = None

    # Required for insert, replace. Optional for cancel.
    # Characteristics of licences can be configured on CHIEF by licence type.
    # including some validation rules and usage reporting options.
    licence_type: Optional[str] = None

    # Required for insert, replace. Optional for cancel.
    # "I" - for Import use, "E" - for Export use.
    usage: Optional[str] = None

    # Required for insert, replace. Optional for cancel.
    # The first date, in format ccyymmdd, for which the licence is valid.
    start_date: Optional[str] = None

    # Optional for insert, replace, cancel.
    end_date: Optional[str] = None


@dataclass
class Trader(_Record):
    type_: Optional[str] = "trader"

    # Must be given if RPATraderId is null.  If given must be known to CHIEF.
    # If "PR" or "UNREG" then name and address must be supplied.
    turn: Optional[str] = None

    # Must be given if TURN is null.
    rpa_trader_id: Optional[str] = None

    # The first and last date, in format ccyymmdd, on which the trader may use
    # the licence.
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # If TURN is "PR" or "UNREG" name, address and postCode must be given.
    # Name is stored as up to 3 lines of 35 characters on CHIEF.
    name: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    address3: Optional[str] = None
    address4: Optional[str] = None
    address5: Optional[str] = None
    postcode: Optional[str] = None


@dataclass
class Country(_Record):
    type_: Optional[str] = "country"

    # Null if group given.
    code: Optional[str] = None

    # Null if code given.
    group: Optional[str] = None

    # "D" Allowed destination country (Exports);
    # "E" Prohibited destination country (Exports);
    # "O" Allowed country of origin (Imports);
    # "P" Prohibited country of origin (Imports);
    # "R" Allowed country en route (for Import whence consigned);
    # "S" Prohibited country en route (for Import whence consigned).
    use: Optional[str] = None


@dataclass
class ForeignTrader(_Record):
    type_: Optional[str] = "foreignTrader"

    # Stored as up to 3 lines of 35 characters on CHIEF.
    name: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    address3: Optional[str] = None
    address4: Optional[str] = None
    address5: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None


@dataclass
class Restrictions(_Record):
    type_: Optional[str] = "restrictions"
    text: Optional[str] = None


@dataclass
class LicenceDataLine(_Record):
    """The `line` data in a licence data (request) message.

    This is not the same as the `line` record in a usage data message.
    """

    type_: Optional[str] = "line"
    line_num: Optional[int] = None

    # Must be null if commodityGroup is supplied.
    commodity: Optional[str] = None

    # Must be absent if commodity is absent.
    supplement1: Optional[str] = None
    supplement2: Optional[str] = None

    # Must be null if commodity is supplied.
    commodity_group: Optional[str] = None

    # Must be supplied if neither commodity nor commodityGroup are given.
    goods_description: Optional[str] = None

    # Identifies how the use of the licence line is controlled:
    # "B" Both Value and Quantity
    # "O" Open (no usage recording or control)
    # "Q" Quantity Only
    # "V" Value Only
    controlled_by: Optional[str] = None

    # Mandatory if controlledBy = "B" or "V".
    currency: Optional[str] = None

    # Mandatory if controlledBy = "B" or "Q".
    quantity_unit: Optional[str] = None

    # Absent if controlledBy = "Q" or "O".
    value_issued: Optional[str] = None

    # Absent if controlledBy = "V" or "O".
    quantity_issued: Optional[str] = None

    # Number of days for sub-period limit. Zero or null denotes that use of
    # the licence is not constrained by sub-period limits. Must not be supplied
    # if controlledBy is "O".
    sub_period: Optional[str] = None

    # The maximum quantity which may be used within any rolling sub-period.
    # Absent if subPeriod is zero or controlledBy = "V".
    sub_period_quantity: Optional[str] = None

    # The maximum value that may be used within any rolling sub-period. Absent
    # if subPeriod is zero. Mandatory if controlledBy = "B" or "V" and
    # subPeriod is non-zero.
    sub_period_value: Optional[str] = None

    # The amount in AFCCurrency per AFCQuantity Unit. A rate of zero can be
    # specified.
    afc_rate: Optional[str] = None

    # Must be specified if AFCRate is given.
    afc_quantity_unit: Optional[str] = None

    # Must be specified if AFCRate is given.
    afc_currency: Optional[str] = None

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
    source_system: Optional[str] = None
    destination_system: Optional[str] = None
    data_id: Optional[str] = None
    creation_date_time: Optional[str] = None
    run_num: Optional[int] = None
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
    transaction_ref: Optional[str] = None
    action: Optional[str] = None
    licence_ref: Optional[str] = None
    licence_type: Optional[str] = None
    usage: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class Trader(_Record):
    type_: Optional[str] = "trader"
    turn: Optional[str] = None
    rpa_trader_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
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
    code: Optional[str] = None
    group: Optional[str] = None
    use: Optional[str] = None


@dataclass
class ForeignTrader(_Record):
    type_: Optional[str] = "foreignTrader"
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
    commodity: Optional[str] = None
    supplement1: Optional[str] = None
    supplement2: Optional[str] = None
    commodity_group: Optional[str] = None
    goods_description: Optional[str] = None
    controlled_by: Optional[str] = None
    currency: Optional[str] = None
    quantity_unit: Optional[str] = None
    value_issued: Optional[str] = None
    quantity_issued: Optional[str] = None
    sub_period: Optional[str] = None
    sub_period_quantity: Optional[str] = None
    sub_period_value: Optional[str] = None
    afc_rate: Optional[str] = None
    afc_quantity_unit: Optional[str] = None
    afc_currency: Optional[str] = None


# Licence usage message.
@dataclass
class LicenceUsage(_Record):
    type_: Optional[str] = "usage"
    transaction_ref: Optional[str] = None
    action: Optional[str] = None
    licence_ref: Optional[str] = None
    licence_status: Optional[str] = None
    completion_date: Optional[str] = None


@dataclass
class LicenceUsageLine(_Record):
    """For use in a licence usage message (not a licence transaction)."""

    type_: Optional[str] = "line"
    line_num: Optional[int] = None
    quantity_used: Optional[str] = None
    value_used: Optional[str] = None
    currency: Optional[str] = None


@dataclass
class Usage(_Record):
    type_: Optional[str] = "usage"
    usage_type: Optional[str] = None
    declaration_urc: Optional[str] = None
    declaration_part_num: Optional[str] = None
    control_date: Optional[str] = None
    quantity_used: Optional[str] = None
    value_used: Optional[str] = None
    currency: Optional[str] = None
    trader_id: Optional[str] = None
    claim_ref: Optional[str] = None
    origin_country: Optional[str] = None
    customs_mic: Optional[str] = None
    customs_message: Optional[str] = None
    consignee_name: Optional[str] = None
    declaration_mrn: Optional[str] = None
    departure_ics: Optional[str] = None

import datetime
import logging
import re
import textwrap
from typing import TYPE_CHECKING, Dict, Iterable, Optional

from django.utils import timezone

from mail.enums import (
    LITE_HMRC_LICENCE_TYPE_MAPPING,
    ChiefSystemEnum,
    ControlledByEnum,
    LicenceActionEnum,
    LicenceTypeEnum,
    UnitMapping,
)
from mail.libraries import chiefprotocol, chieftypes
from mail.libraries.edifact_validator import (
    FOREIGN_TRADER_ADDR_LINE_MAX_LEN,
    FOREIGN_TRADER_NUM_ADDR_LINES,
    validate_edifact_file,
)
from mail.libraries.helpers import get_country_id
from mail.models import GoodIdMapping, LicencePayload

if TYPE_CHECKING:
    from django.db.models import QuerySet  # noqa


class EdifactValidationError(Exception):
    pass


def generate_lines_for_licence(licence: LicencePayload) -> Iterable[chieftypes._Record]:
    """Yield line tuples for a single licence, to use in a CHIEF message.

    The line tuples have no numbering (line numbers are calculated after
    all lines have been gathered).
    """
    usage_code = "E"  # "E" for export. CHIEF also does "I" for import.
    payload = licence.data
    licence_type = LITE_HMRC_LICENCE_TYPE_MAPPING.get(payload.get("type"))

    if licence.action == LicenceActionEnum.UPDATE:
        # An "update" is represented by a cancel for the old licence ref,
        # followed by an "insert" for the new ref.
        old_reference = licence.old_reference
        old_payload = LicencePayload.objects.get(reference=old_reference).data
        yield chieftypes.Licence(
            transaction_ref=get_transaction_reference(old_reference),
            action="cancel",
            licence_ref=old_reference,
            licence_type=licence_type,
            usage=usage_code,
            start_date=old_payload.get("start_date").replace("-", ""),
            end_date=old_payload.get("end_date").replace("-", ""),
        )
        yield chieftypes.End(start_record_type=chieftypes.Licence.type_)

        yield chieftypes.Licence(
            transaction_ref=get_transaction_reference(licence.reference),
            action="insert",
            licence_ref=licence.reference,
            licence_type=licence_type,
            usage=usage_code,
            start_date=payload.get("start_date").replace("-", ""),
            end_date=payload.get("end_date").replace("-", ""),
        )
    else:
        yield chieftypes.Licence(
            transaction_ref=get_transaction_reference(licence.reference),
            action=licence.action,
            licence_ref=licence.reference,
            licence_type=licence_type,
            usage=usage_code,
            start_date=payload.get("start_date").replace("-", ""),
            end_date=payload.get("end_date").replace("-", ""),
        )

    if licence.action != LicenceActionEnum.CANCEL:
        trader = payload.get("organisation")
        trader = sanitize_trader_address(trader)

        yield chieftypes.Trader(
            rpa_trader_id=trader.get("eori_number", ""),
            start_date=payload.get("start_date").replace("-", ""),
            end_date=payload.get("end_date").replace("-", ""),
            name=trader.get("name"),
            address1=trader.get("address").get("line_1"),
            address2=trader.get("address").get("line_2", ""),
            address3=trader.get("address").get("line_3", ""),
            address4=trader.get("address").get("line_4", ""),
            address5=trader.get("address").get("line_5", ""),
            postcode=trader.get("address").get("postcode"),
        )

        # Uses "D" for licence use because lite only sends allowed countries, to use E would require changes on the API
        if payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
            if payload.get("country_group"):
                yield chieftypes.Country(group=payload.get("country_group"), use="D")

            elif payload.get("countries"):
                for country in payload.get("countries"):
                    country_id = get_country_id(country)
                    yield chieftypes.Country(code=country_id, use="D")

        elif payload.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
            if payload.get("end_user"):
                # In the absence of country_group or countries use country of End user
                country = payload.get("end_user").get("address").get("country")
                country_id = get_country_id(country)
                yield chieftypes.Country(code=country_id, use="D")

        if payload.get("end_user"):
            trader = payload.get("end_user")
            trader = sanitize_foreign_trader_address(trader)

            yield chieftypes.ForeignTrader(
                name=trader.get("name"),
                address1=trader.get("address").get("line_1"),
                address2=trader.get("address").get("line_2", ""),
                address3=trader.get("address").get("line_3", ""),
                address4=trader.get("address").get("line_4", ""),
                address5=trader.get("address").get("line_5", ""),
                postcode=trader.get("address").get("postcode", ""),
                country=get_country_id(trader.get("address").get("country")),
            )

        yield chieftypes.Restrictions(text="Provisos may apply please see licence")

        if payload.get("goods") and payload.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
            for g, commodity in enumerate(payload.get("goods"), start=1):
                GoodIdMapping.objects.get_or_create(
                    lite_id=commodity["id"], licence_reference=licence.reference, line_number=g
                )
                controlled_by = "Q"  # usage is controlled by quantity only
                quantity = commodity.get("quantity")
                qunit = UnitMapping[commodity["unit"]]

                if qunit == UnitMapping.NAR:
                    quantity = int(quantity)

                yield chieftypes.LicenceDataLine(
                    line_num=g,
                    goods_description=commodity.get("name"),
                    controlled_by=controlled_by,
                    quantity_unit="{:03d}".format(qunit.value),
                    quantity_issued=quantity,
                )

        if payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
            yield chieftypes.LicenceDataLine(
                line_num=1,
                goods_description="Open Licence goods - see actual licence for information",
            )

    yield chieftypes.End(start_record_type=chieftypes.Licence.type_)


def licences_to_edifact(
    licences: "QuerySet[LicencePayload]", run_number: int, source: str, when: datetime.datetime = None
) -> str:
    # Build a list of lines, with each line a tuple. After we have all the
    # lines, we format them ("\" as field separator) and insert the line
    # numbers. Some lines reference previous line numbers, so we need to
    # track those.
    lines = []

    if not when:
        when = timezone.now()

    time_stamp = when.strftime("%Y%m%d%H%M")  # YYYYMMDDhhmm

    # Setting this to Y will override the hmrc run number with the run number in this file.
    # This is usually set to N in almost all cases
    reset_run_number_indicator = "N"
    dest_system = "CHIEF"
    file_header = chieftypes.FileHeader(
        source_system=source,  # Like "SPIRE" or "ILBDOTI".
        destination_system=dest_system,
        data_id="licenceData",
        creation_date_time=time_stamp,
        run_num=run_number,
        reset_run_num=reset_run_number_indicator,
    )
    lines.append(file_header)

    logging.info("File header: %r", file_header)

    if source == ChiefSystemEnum.ICMS:
        get_licence_lines = generate_lines_for_icms_licence
    else:
        get_licence_lines = generate_lines_for_licence

    for licence in licences:
        lines.extend(get_licence_lines(licence))

    # File trailer includes the number of licences, but +1 for each "update"
    # because this code represents those as "cancel" followed by "insert".
    num_transactions = chiefprotocol.count_transactions(lines)
    file_trailer = chieftypes.FileTrailer(transaction_count=num_transactions)
    lines.append(file_trailer)

    # Convert line tuples to the final string with line numbers, etc.
    edifact_file = chiefprotocol.format_lines(lines)

    logging.debug("Generated file content: %r", edifact_file)
    errors = validate_edifact_file(edifact_file)
    if errors:
        logging.error("File content not as per specification, %r", errors)
        raise EdifactValidationError(repr(errors))

    return edifact_file


def get_transaction_reference(licence_reference: str) -> str:
    if licence_reference.startswith("GB"):
        licence_reference = licence_reference.split("/", 1)[1]
        return licence_reference.replace("/", "")
    else:
        match_first_digit = re.search(r"\d", licence_reference)
        if not match_first_digit:
            raise ValueError("Invalid Licence reference")
        return licence_reference[match_first_digit.start() :].replace("-", "")


def sanitize_foreign_trader_address(trader):
    """
    Foreign trader/End user address is currently a single text field.
    User may enter in multiple lines or in a single line separated so we try to
    break them in chunks of 35 chars and populate them as address lines
    """
    address = trader["address"]

    addr_line = address.pop("line_1")
    addr_line = addr_line.replace("\n", " ").replace("\r", " ")
    # replace special characters
    addr_line = addr_line.replace("#", "")
    addr_lines = textwrap.wrap(addr_line, width=FOREIGN_TRADER_ADDR_LINE_MAX_LEN, break_long_words=False)
    if len(addr_lines) > FOREIGN_TRADER_NUM_ADDR_LINES:
        addr_lines = addr_lines[:FOREIGN_TRADER_NUM_ADDR_LINES]

    for index, line in enumerate(addr_lines, start=1):
        address[f"line_{index}"] = line

    return trader


def sanitize_trader_address(trader):
    """
    Trader address is split into 5 lines.
    When any since one of these lines exceed 35 chars we need to break then up into lines
    There is a possibility of truncating the address here if this happens we log it
    """
    address = trader["address"]

    addr_line = " ".join(address.get(f"line_{i+1}") for i in range(5) if address.get(f"line_{i+1}"))

    addr_line = addr_line.replace("\n", " ").replace("\r", " ")
    # replace special characters
    addr_line = addr_line.replace("#", "")
    addr_lines = textwrap.wrap(addr_line, width=FOREIGN_TRADER_ADDR_LINE_MAX_LEN, break_long_words=False)
    if len(addr_lines) > FOREIGN_TRADER_NUM_ADDR_LINES:
        addr_lines = addr_lines[:FOREIGN_TRADER_NUM_ADDR_LINES]
        logging.info(
            "Truncating trader address as we exceeded %d, original_address: %s, truncated_address: %s",
            FOREIGN_TRADER_ADDR_LINE_MAX_LEN,
            addr_line,
            addr_lines,
        )

    for index, line in enumerate(addr_lines, start=1):
        address[f"line_{index}"] = line

    return trader


def generate_lines_for_icms_licence(licence: LicencePayload) -> Iterable[chieftypes._Record]:
    """Yield lines for a single ICMS licence, to use in a CHIEF message."""

    payload = licence.data
    usage_code = "I"
    icms_licence_type = payload["type"]
    chief_licence_type = LITE_HMRC_LICENCE_TYPE_MAPPING[icms_licence_type]

    # ICMS only sends "insert", "replace" or "cancel" payloads.
    # If there are errors with a "replace" the licence is normally revoked within ICMS and a
    # new licence is applied for with the new requirements.
    supported_actions = [LicenceActionEnum.INSERT, LicenceActionEnum.REPLACE]

    if licence.action not in supported_actions:
        raise NotImplementedError(f"Action {licence.action} not supported yet")

    yield chieftypes.Licence(
        action=licence.action,
        # reference = ICMS case reference
        transaction_ref=payload["reference"],
        licence_ref=payload["licence_reference"],
        licence_type=chief_licence_type,
        usage=usage_code,
        start_date=get_date_field(payload, "start_date"),
        end_date=get_date_field(payload, "end_date"),
    )

    trader = payload.get("organisation")
    trader_address = trader.get("address")

    yield chieftypes.Trader(
        rpa_trader_id=trader.get("eori_number"),
        start_date=get_date_field(trader, "start_date"),
        end_date=get_date_field(trader, "end_date"),
        name=trader.get("name"),
        address1=trader_address.get("line_1"),
        address2=trader_address.get("line_2"),
        address3=trader_address.get("line_3"),
        address4=trader_address.get("line_4"),
        address5=trader_address.get("line_5"),
        postcode=trader_address.get("postcode"),
    )

    kwargs = {"use": "O"}
    if payload.get("country_group"):
        yield chieftypes.Country(group=payload.get("country_group"), **kwargs)

    elif payload.get("country_code"):
        yield chieftypes.Country(code=payload.get("country_code"), **kwargs)

    yield get_restrictions(licence)

    for g in get_goods(icms_licence_type, payload.get("goods")):
        yield g

    yield chieftypes.End(start_record_type=chieftypes.Licence.type_)


def get_date_field(obj, key, default="") -> str:
    val = obj.get(key)

    if not val:
        return default

    return val.replace("-", "")


def get_restrictions(licence: LicencePayload) -> chieftypes.Restrictions:
    restrictions: str = licence.data.get("restrictions", "")
    text = restrictions.replace("\n", "|").strip()

    return chieftypes.Restrictions(text=text)


def get_goods(licence_type: str, goods: Optional[list]) -> Iterable[chieftypes.Restrictions]:
    if not goods:
        return []

    goods_iter = enumerate(goods, start=1)

    # Sanctions
    if licence_type == LicenceTypeEnum.IMPORT_SAN:
        for idx, good in goods_iter:
            kwargs = _get_controlled_by_kwargs(good)

            yield chieftypes.LicenceDataLine(line_num=idx, commodity=good["commodity"], **kwargs)

    # FA-SIL
    elif licence_type == LicenceTypeEnum.IMPORT_SIL:
        for idx, good in goods_iter:
            kwargs = _get_controlled_by_kwargs(good)

            yield chieftypes.LicenceDataLine(line_num=idx, goods_description=good["description"], **kwargs)

    # FA-DFL and FA-OIL
    else:
        for idx, good in goods_iter:
            yield chieftypes.LicenceDataLine(
                line_num=idx, goods_description=good["description"], controlled_by=ControlledByEnum.OPEN
            )


def _get_controlled_by_kwargs(good: Dict[str, str]) -> Dict[str, str]:
    controlled_by = good["controlled_by"]
    kwargs = {"controlled_by": controlled_by}

    if controlled_by == ControlledByEnum.QUANTITY:
        unit = int(good["unit"])
        kwargs["quantity_unit"] = f"{unit:03}"
        kwargs["quantity_issued"] = good["quantity"]

    return kwargs

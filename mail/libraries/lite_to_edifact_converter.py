import logging
import re
import textwrap
from typing import Iterable

from django.utils import timezone

from mail.enums import LITE_HMRC_LICENCE_TYPE_MAPPING, LicenceActionEnum, LicenceTypeEnum, UnitMapping
from mail.libraries import chiefprotocol, chieftypes
from mail.libraries.edifact_validator import (
    FOREIGN_TRADER_ADDR_LINE_MAX_LEN,
    FOREIGN_TRADER_NUM_ADDR_LINES,
    validate_edifact_file,
)
from mail.libraries.helpers import get_country_id
from mail.models import GoodIdMapping, LicencePayload


class EdifactValidationError(Exception):
    pass


def generate_lines_for_licence(licence):
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
                if commodity.get("unit") == "NAR":
                    quantity = int(quantity)

                yield chieftypes.LicenceDataLine(
                    line_num=g,
                    goods_description=commodity.get("name"),
                    controlled_by=controlled_by,
                    quantity_unit="{:03d}".format(UnitMapping.convert(commodity.get("unit"))),
                    quantity_issued=quantity,
                )

        if payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
            yield chieftypes.LicenceDataLine(
                line_num=1,
                goods_description="Open Licence goods - see actual licence for information",
            )

    yield chieftypes.End(start_record_type=chieftypes.Licence.type_)


def licences_to_edifact(licences: Iterable[LicencePayload], run_number: int) -> str:
    # Build a list of lines, with each line a tuple. After we have all the
    # lines, we format them ("\" as field separator) and insert the line
    # numbers. Some lines reference previous line numbers, so we need to
    # track those.
    lines = []

    time_stamp = timezone.now().strftime("%Y%m%d%H%M")  # YYYYMMDDhhmm
    # Setting this to Y will override the hmrc run number with the run number in this file.
    # This is usually set to N in almost all cases
    reset_run_number_indicator = "N"
    src_system = "SPIRE"
    dest_system = "CHIEF"
    file_header = chieftypes.FileHeader(
        source_system=src_system,
        destination_system=dest_system,
        data_id="licenceData",
        creation_date_time=time_stamp,
        run_num=run_number,
        reset_run_num=reset_run_number_indicator,
    )
    lines.append(file_header)

    logging.info(f"File header:{file_header}")

    for licence in licences:
        licence_lines = list(generate_lines_for_licence(licence))
        lines.extend(licence_lines)

    # File trailer includes the number of licences, but +1 for each "update"
    # because this code represents those as "cancel" followed by "insert".
    num_transactions = chiefprotocol.count_transactions(lines)
    file_trailer = ("fileTrailer", num_transactions)
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

import logging
import textwrap

from django.db.models import QuerySet
from django.utils import timezone

from mail.enums import UnitMapping, LicenceActionEnum, LicenceTypeEnum, LITE_HMRC_LICENCE_TYPE_MAPPING
from mail.libraries.helpers import get_country_id
from mail.models import GoodIdMapping, LicencePayload
from mail.libraries.edifact_validator import (
    validate_edifact_file,
    FOREIGN_TRADER_NUM_ADDR_LINES,
    FOREIGN_TRADER_ADDR_LINE_MAX_LEN,
)
from mail.libraries import chiefprotocol


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
        yield (
            "licence",
            get_transaction_reference(old_reference),
            "cancel",
            old_reference,
            licence_type,
            usage_code,
            old_payload.get("start_date").replace("-", ""),
            old_payload.get("end_date").replace("-", ""),
        )
        yield ("end", "licence")

        yield (
            "licence",
            get_transaction_reference(licence.reference),
            "insert",
            licence.reference,
            licence_type,
            usage_code,
            payload.get("start_date").replace("-", ""),
            payload.get("end_date").replace("-", ""),
        )
    else:
        yield (
            "licence",
            get_transaction_reference(licence.reference),
            licence.action,
            licence.reference,
            licence_type,
            usage_code,
            payload.get("start_date").replace("-", ""),
            payload.get("end_date").replace("-", ""),
        )

    if licence.action != LicenceActionEnum.CANCEL:
        trader = payload.get("organisation")

        yield (
            "trader",
            "",  # turn
            trader.get("eori_number", ""),
            payload.get("start_date").replace("-", ""),
            payload.get("end_date").replace("-", ""),
            trader.get("name"),
            trader.get("address").get("line_1"),
            trader.get("address").get("line_2", ""),
            trader.get("address").get("line_3", ""),
            trader.get("address").get("line_4", ""),
            trader.get("address").get("line_5", ""),
            trader.get("address").get("postcode"),
        )

        # Uses "D" for licence use because lite only sends allowed countries, to use E would require changes on the API
        if payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
            if payload.get("country_group"):
                yield ("country", None, payload.get("country_group"), "D")

            elif payload.get("countries"):
                for country in payload.get("countries"):
                    country_id = get_country_id(country)
                    yield ("country", country_id, None, "D")

        elif payload.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
            if payload.get("end_user"):
                # In the absence of country_group or countries use country of End user
                country = payload.get("end_user").get("address").get("country")
                country_id = get_country_id(country)
                yield ("country", country_id, None, "D")

        if payload.get("end_user"):
            trader = payload.get("end_user")
            trader = sanitize_foreign_trader_address(trader)

            yield (
                "foreignTrader",
                trader.get("name"),
                trader.get("address").get("line_1"),
                trader.get("address").get("line_2", ""),
                trader.get("address").get("line_3", ""),
                trader.get("address").get("line_4", ""),
                trader.get("address").get("line_5", ""),
                trader.get("address").get("postcode", ""),
                get_country_id(trader.get("address").get("country")),
            )

        yield ("restrictions", "Provisos may apply please see licence")

        if payload.get("goods") and payload.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
            for g, commodity in enumerate(payload.get("goods"), start=1):
                GoodIdMapping.objects.get_or_create(
                    lite_id=commodity["id"], licence_reference=licence.reference, line_number=g
                )
                controlled_by = "Q"  # usage is controlled by quantity only
                quantity = commodity.get("quantity")
                if commodity.get("unit") == "NAR":
                    quantity = int(quantity)

                yield (
                    "line",
                    g,
                    None,
                    None,
                    None,
                    None,
                    commodity.get("name"),
                    controlled_by,
                    None,
                    "{:03d}".format(UnitMapping.convert(commodity.get("unit"))),
                    None,
                    quantity,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                )

        if payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
            yield (
                "line",
                1,
                None,
                None,
                None,
                None,
                "Open Licence goods - see actual licence for information",
                None,
            )


def licences_to_edifact(licences: QuerySet, run_number: int) -> str:
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
    file_header = (
        "fileHeader",
        src_system,
        dest_system,
        "licenceData",
        time_stamp,
        run_number,
        reset_run_number_indicator,
    )
    lines.append(file_header)

    logging.info(f"File header:{file_header}")

    for licence in licences:
        licence_lines = list(generate_lines_for_licence(licence))
        lines.extend(licence_lines)
        end_licence = ("end", "licence")
        lines.append(end_licence)

    # File trailer includes the number of licences, but +1 for each "update"
    # because this code represents those as "cancel" followed by "insert".
    num_transactions = licences.count() + licences.filter(action=LicenceActionEnum.UPDATE).count()
    file_trailer = ("fileTrailer", num_transactions)
    lines.append(file_trailer)

    # Convert line tuples to the final string with line numbers, etc.
    edifact_file = chiefprotocol.format_lines(lines)

    logging.debug("Generated file content: %r", edifact_file)
    errors = validate_edifact_file(edifact_file)
    if errors:
        logging.error("File content not as per specification, %r", errors)
        raise EdifactValidationError

    return edifact_file


def get_transaction_reference(licence_reference: str) -> str:
    licence_reference = licence_reference.split("/", 1)[1]
    return licence_reference.replace("/", "")


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

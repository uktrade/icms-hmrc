import datetime
import logging
from typing import TYPE_CHECKING, Dict, Iterable, Optional

from django.utils import timezone

from mail.enums import ICMS_HMRC_LICENCE_TYPE_MAPPING, ControlledByEnum, LicenceActionEnum, LicenceTypeEnum
from mail.libraries import chiefprotocol, chieftypes
from mail.libraries.edifact_validator import validate_edifact_file
from mail.models import LicencePayload

if TYPE_CHECKING:
    from django.db.models import QuerySet  # noqa


class EdifactValidationError(Exception):
    pass


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
        source_system=source,  # "ILBDOTI".
        destination_system=dest_system,
        data_id="licenceData",
        creation_date_time=time_stamp,
        run_num=run_number,
        reset_run_num=reset_run_number_indicator,
    )
    lines.append(file_header)

    logging.info("File header: %r", file_header)

    for licence in licences:
        lines.extend(generate_lines_for_icms_licence(licence))

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


def generate_lines_for_icms_licence(licence: LicencePayload) -> Iterable[chieftypes._Record]:
    """Yield lines for a single ICMS licence, to use in a CHIEF message."""

    payload = licence.data
    usage_code = "I"
    icms_licence_type = payload["type"]
    chief_licence_type = ICMS_HMRC_LICENCE_TYPE_MAPPING[icms_licence_type]

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

import datetime
import json
import logging
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from mail.chief.licence_data import chiefprotocol, types
from mail.chief.licence_data.edifact_validator import validate_edifact_file
from mail.enums import (
    ICMS_HMRC_LICENCE_TYPE_MAPPING,
    ControlledByEnum,
    ExtractTypeEnum,
    LicenceActionEnum,
    LicenceTypeEnum,
    SourceEnum,
)
from mail.models import LicenceData, LicencePayload, Mail

if TYPE_CHECKING:
    from django.db.models import QuerySet  # noqa


logger = logging.getLogger(__name__)


def create_licence_data_mail(licences: "QuerySet[LicencePayload]", source: SourceEnum) -> Mail:
    last_licence_data = LicenceData.objects.last()
    run_number = last_licence_data.hmrc_run_number + 1 if last_licence_data else 1
    when = timezone.now()

    file_name, file_content = build_licence_data_file(licences, run_number, when)

    mail = Mail.objects.create(
        edi_filename=file_name,
        edi_data=file_content,
        extract_type=ExtractTypeEnum.LICENCE_DATA,
    )
    logger.info("New Mail instance (%s) created for filename %s", mail.id, file_name)
    licence_ids = json.dumps([licence.reference for licence in licences])
    licence_data = LicenceData.objects.create(
        hmrc_run_number=run_number, source=source, mail=mail, licence_ids=licence_ids
    )

    # Keep a reference of all licence_payloads linked to this LicenceData instance
    licence_data.licence_payloads.set(licences)

    return mail


def build_licence_data_file(
    licences: "QuerySet[LicencePayload]", run_number: int, when: datetime.datetime
) -> Tuple[str, str]:
    system = settings.CHIEF_SOURCE_SYSTEM
    file_name = f"CHIEF_LIVE_{system}_licenceData_{run_number}_{when:%Y%m%d%H%M}"
    logger.info("Building licenceData file %s for %s licences", file_name, licences.count())

    file_content = licences_to_edifact(licences, run_number, system, when)

    return file_name, file_content


def licences_to_edifact(
    licences: "QuerySet[LicencePayload]",
    run_number: int,
    source: str,
    when: datetime.datetime = None,
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
    file_header = types.FileHeader(
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
    file_trailer = types.FileTrailer(transaction_count=num_transactions)
    lines.append(file_trailer)

    # Convert line tuples to the final string with line numbers, etc.
    edifact_file = chiefprotocol.format_lines(lines)

    logging.debug("Generated file content: %r", edifact_file)
    errors = validate_edifact_file(edifact_file)
    if errors:
        logging.error("File content not as per specification, %r", errors)
        raise ValueError(repr(errors))

    return edifact_file


def generate_lines_for_icms_licence(licence: LicencePayload) -> Iterable[types._Record]:
    """Yield lines for a single ICMS licence, to use in a CHIEF message."""

    payload = licence.data
    usage_code = "I"
    icms_licence_type = payload["type"]
    chief_licence_type = ICMS_HMRC_LICENCE_TYPE_MAPPING[icms_licence_type]

    # ICMS only sends "insert", "replace" or "cancel" payloads.
    # If there are errors with a "replace" the licence is normally revoked within ICMS and a
    # new licence is applied for with the new requirements.
    supported_actions = [
        LicenceActionEnum.INSERT,
        LicenceActionEnum.REPLACE,
        LicenceActionEnum.CANCEL,
    ]

    if licence.action not in supported_actions:
        raise NotImplementedError(f"Action {licence.action} not supported yet")

    # Section required for all action types
    yield types.Licence(
        # reference = ICMS case reference
        transaction_ref=payload["reference"],
        action=licence.action,
        licence_ref=payload["licence_reference"],
        licence_type=chief_licence_type,
        usage=usage_code,
        start_date=get_date_field(payload, "start_date"),
        end_date=get_date_field(payload, "end_date"),
    )

    # Sections required for INSERT & REPLACE
    if licence.action in [LicenceActionEnum.INSERT, LicenceActionEnum.REPLACE]:
        trader = payload.get("organisation")
        trader_address = trader.get("address")

        yield types.Trader(
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
            yield types.Country(group=payload.get("country_group"), **kwargs)

        elif payload.get("country_code"):
            yield types.Country(code=payload.get("country_code"), **kwargs)

        yield get_restrictions(licence)

        for g in get_goods(icms_licence_type, payload.get("goods")):
            yield g

    # Section required for all action types
    yield types.End(start_record_type=types.Licence.type_)


def get_date_field(obj, key, default="") -> str:
    val = obj.get(key)

    if not val:
        return default

    return val.replace("-", "")


def get_restrictions(licence: LicencePayload) -> types.Restrictions:
    restrictions: str = licence.data.get("restrictions", "")
    text = restrictions.replace("\n", "|").strip()

    return types.Restrictions(text=text)


def get_goods(licence_type: str, goods: Optional[list]) -> Iterable[types.Restrictions]:
    if not goods:
        return []

    goods_iter = enumerate(goods, start=1)

    # Sanctions
    if licence_type == LicenceTypeEnum.IMPORT_SAN:
        for idx, good in goods_iter:
            kwargs = _get_controlled_by_kwargs(good)

            yield types.LicenceDataLine(line_num=idx, commodity=good["commodity"], **kwargs)

    # FA-SIL
    elif licence_type == LicenceTypeEnum.IMPORT_SIL:
        for idx, good in goods_iter:
            kwargs = _get_controlled_by_kwargs(good)

            yield types.LicenceDataLine(
                line_num=idx, goods_description=good["description"], **kwargs
            )

    # FA-DFL and FA-OIL
    else:
        for idx, good in goods_iter:
            yield types.LicenceDataLine(
                line_num=idx,
                goods_description=good["description"],
                controlled_by=ControlledByEnum.OPEN,
            )


def _get_controlled_by_kwargs(good: Dict[str, str]) -> Dict[str, str]:
    controlled_by = good["controlled_by"]
    kwargs = {"controlled_by": controlled_by}

    if controlled_by == ControlledByEnum.QUANTITY:
        unit = int(good["unit"])
        kwargs["quantity_unit"] = f"{unit:03}"
        kwargs["quantity_issued"] = good["quantity"]

    return kwargs

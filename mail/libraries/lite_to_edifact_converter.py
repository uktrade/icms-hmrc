from django.db.models import QuerySet
from django.utils import timezone

from mail.enums import UnitMapping, LicenceActionEnum, LicenceTypeEnum
from mail.libraries.helpers import get_country_id
from mail.models import OrganisationIdMapping, GoodIdMapping, LicencePayload


LITE_HMRC_LICENCE_TYPE_MAPPING = {
    "siel": "SIE",
    "sicl": "SIE",
    "sitl": "SIE",
    "oiel": "OIE",
    "oiel": "OIE",
    "ogel": "OGE",
    "ogcl": "OGE",
    "ogtl": "OGE",
}


def licences_to_edifact(licences: QuerySet, run_number: int) -> str:
    now = timezone.now()
    time_stamp = "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)

    edifact_file = "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\{}\\{}\\Y".format(time_stamp, run_number)

    line_no = 1
    for licence in licences:
        licence_payload = licence.data
        licence_type = LITE_HMRC_LICENCE_TYPE_MAPPING.get(licence_payload.get("type"))
        start_line = line_no
        line_no += 1

        if licence.action == LicenceActionEnum.UPDATE:
            old_reference = licence.old_reference
            old_payload = LicencePayload.objects.get(reference=old_reference).data
            edifact_file += "\n{}\\licence\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                line_no,
                get_transaction_reference(old_reference),  # transaction_reference
                "cancel",
                old_reference,
                licence_type,
                "E",  # Export use
                old_payload.get("start_date").replace("-", ""),
                old_payload.get("end_date").replace("-", ""),
            )
            line_no += 1
            edifact_file += "\n{}\\end\\licence\\{}".format(line_no, line_no - start_line)
            start_line = line_no
            line_no += 1
            edifact_file += "\n{}\\licence\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                line_no,
                get_transaction_reference(licence.reference),  # transaction_reference
                "insert",
                licence.reference,
                licence_type,
                "E",  # Export use
                licence_payload.get("start_date").replace("-", ""),
                licence_payload.get("end_date").replace("-", ""),
            )
        else:
            edifact_file += "\n{}\\licence\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                line_no,
                get_transaction_reference(licence.reference),  # transaction_reference
                licence.action,
                licence.reference,
                licence_type,
                "E",
                licence_payload.get("start_date").replace("-", ""),
                licence_payload.get("end_date").replace("-", ""),
            )
        if licence.action != LicenceActionEnum.CANCEL:
            trader = licence_payload.get("organisation")
            org_mapping, _ = OrganisationIdMapping.objects.get_or_create(
                lite_id=trader["id"], defaults={"lite_id": trader["id"]}
            )
            line_no += 1
            edifact_file += "\n{}\\trader\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                line_no,
                "",  # turn
                org_mapping.rpa_trader_id,
                licence_payload.get("start_date").replace("-", ""),
                licence_payload.get("end_date").replace("-", ""),
                trader.get("name"),
                trader.get("address").get("line_1"),
                trader.get("address").get("line_2", ""),
                trader.get("address").get("line_3", ""),
                trader.get("address").get("line_4", ""),
                trader.get("address").get("line_5", ""),
                trader.get("address").get("postcode"),
            )
            # Uses "D" for licence use because lite only sends allowed countries, to use E would require changes on the API
            if licence_payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
                if licence_payload.get("country_group"):
                    line_no += 1
                    edifact_file += "\n{}\\country\\\\{}\\{}".format(line_no, licence_payload.get("country_group"), "D")
                elif licence_payload.get("countries"):
                    for country in licence_payload.get("countries"):
                        country_id = get_country_id(country)
                        line_no += 1
                        edifact_file += "\n{}\\country\\{}\\\\{}".format(line_no, country_id, "D")
            elif licence_payload.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
                if licence_payload.get("end_user"):
                    # In the absence of country_group or countries use country of End user
                    country_id = licence_payload.get("end_user").get("address").get("country").get("id")
                    line_no += 1
                    edifact_file += "\n{}\\country\\{}\\\\{}".format(line_no, country_id, "D")

            if licence_payload.get("end_user"):
                trader = licence_payload.get("end_user")
                line_no += 1
                edifact_file += "\n{}\\foreignTrader\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                    line_no,
                    trader.get("name"),
                    trader.get("address").get("line_1"),
                    trader.get("address").get("line_2", ""),
                    trader.get("address").get("line_3", ""),
                    trader.get("address").get("line_4", ""),
                    trader.get("address").get("line_5", ""),
                    trader.get("address").get("postcode", ""),
                    trader.get("address").get("country").get("id"),
                )
            line_no += 1
            edifact_file += "\n{}\\restrictions\\{}".format(line_no, "Provisos may apply please see licence")
            if licence_payload.get("goods") and licence_payload.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
                for g, commodity in enumerate(licence_payload.get("goods"), start=1):
                    line_no += 1
                    GoodIdMapping.objects.get_or_create(
                        lite_id=commodity["id"], licence_reference=licence.reference, line_number=g
                    )
                    controlled_by = "Q"  # usage is controlled by quantity only
                    edifact_file += "\n{}\\line\\{}\\\\\\\\\\{}\\{}\\\\{:03d}\\\\{}".format(
                        line_no,
                        g,
                        commodity.get("name"),
                        controlled_by,
                        UnitMapping.convert(commodity.get("unit")),
                        int(commodity.get("quantity")) if commodity.get("unit") == "NAR" else commodity.get("quantity"),
                    )
            if licence_payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
                line_no += 1
                edifact_file += (
                    "\n{}\\line\\1\\\\\\\\\\Open Licence goods - see actual licence for information\\".format(line_no)
                )
        line_no += 1
        edifact_file += "\n{}\\end\\licence\\{}".format(line_no, line_no - start_line)
    line_no += 1
    edifact_file += "\n{}\\fileTrailer\\{}".format(
        line_no, licences.count() + licences.filter(action=LicenceActionEnum.UPDATE).count()
    )
    return edifact_file


def get_transaction_reference(licence_reference: str) -> str:
    licence_reference = licence_reference.split("/", 1)[1]
    return licence_reference.replace("/", "")

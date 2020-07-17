from django.db.models import QuerySet
from django.utils import timezone

from mail.enums import UnitMapping, LicenceActionEnum, LicenceTypeEnum
from mail.models import OrganisationIdMapping, GoodIdMapping, LicencePayload


def licences_to_edifact(licences: QuerySet, run_number: int) -> str:
    now = timezone.now()
    time_stamp = "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
    edifact_file = "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\{}\\{}".format(time_stamp, run_number)
    i = 1
    for licence in licences:
        licence_payload = licence.data
        start_line = i
        i += 1
        if licence.action == LicenceActionEnum.UPDATE:
            old_reference = licence.old_reference
            old_payload = LicencePayload.objects.get(reference=old_reference).data
            edifact_file += "\n{}\\licence\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                i,
                get_transaction_reference(old_reference),  # transaction_reference
                "cancel",
                old_reference,
                licence_payload.get("type"),
                "E",
                old_payload.get("start_date").replace("-", ""),
                old_payload.get("end_date").replace("-", ""),
            )
            i += 1
            edifact_file += "\n{}\\end\\licence\\{}".format(i, i - start_line)
            start_line = i
            i += 1
            edifact_file += "\n{}\\licence\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                i,
                get_transaction_reference(licence.reference),  # transaction_reference
                "insert",
                licence.reference,
                licence_payload.get("type"),
                "E",
                licence_payload.get("start_date").replace("-", ""),
                licence_payload.get("end_date").replace("-", ""),
            )
        else:
            edifact_file += "\n{}\\licence\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                i,
                get_transaction_reference(licence.reference),  # transaction_reference
                licence.action,
                licence.reference,
                licence_payload.get("type"),
                "E",
                licence_payload.get("start_date").replace("-", ""),
                licence_payload.get("end_date").replace("-", ""),
            )
        if licence.action != LicenceActionEnum.CANCEL:
            trader = licence_payload.get("organisation")
            org_mapping, _ = OrganisationIdMapping.objects.get_or_create(
                lite_id=trader["id"], defaults={"lite_id": trader["id"]}
            )
            i += 1
            edifact_file += "\n{}\\trader\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                i,
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
            if licence_payload.get("country_group"):
                i += 1
                edifact_file += "\n{}\\country\\\\{}\\{}".format(
                    i, licence_payload.get("country_group"), licence_payload.get("use")
                )
            elif licence_payload.get("countries"):
                for country in licence_payload.get("countries"):
                    i += 1
                    edifact_file += "\n{}\\country\\{}\\\\{}".format(i, country, licence_payload.get("use"))
            if licence_payload.get("end_user"):
                trader = licence_payload.get("end_user")
                i += 1
                edifact_file += "\n{}\\foreignTrader\\{}\\{}\\{}\\{}\\{}\\{}\\{}\\{}".format(
                    i,
                    trader.get("name"),
                    trader.get("address").get("line_1"),
                    trader.get("address").get("line_2", ""),
                    trader.get("address").get("line_3", ""),
                    trader.get("address").get("line_4", ""),
                    trader.get("address").get("line_5", ""),
                    trader.get("address").get("postcode", ""),
                    trader.get("address").get("country").get("id"),
                )
            i += 1
            edifact_file += "\n{}\\restrictions\\{}".format(i, "Provisos may apply please see licence")
            g = 0
            if licence_payload.get("goods") and licence_payload.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
                for commodity in licence_payload.get("goods"):
                    i += 1
                    g += 1
                    GoodIdMapping.objects.get_or_create(
                        lite_id=commodity["id"], licence_reference=licence.reference, line_number=g
                    )
                    edifact_file += "\n{}\\line\\{}\\\\\\\\\\{}\\Q\\{}\\{}".format(
                        i,
                        g,
                        commodity.get("description"),
                        UnitMapping.convert(commodity.get("unit")),
                        int(commodity.get("quantity")) if commodity.get("unit") == "NAR" else commodity.get("quantity"),
                    )
            if licence_payload.get("type") in LicenceTypeEnum.OPEN_LICENCES:
                i += 1
                edifact_file += "\n{}\\line\\1\\\\\\\\\\Open Licence goods - see actual licence for information\\".format(
                    i
                )
        i += 1
        edifact_file += "\n{}\\end\\licence\\{}".format(i, i - start_line)
    i += 1
    edifact_file += "\n{}\\fileTrailer\\{}".format(
        i, licences.count() + licences.filter(action=LicenceActionEnum.UPDATE).count()
    )
    return edifact_file


def get_transaction_reference(licence_reference: str) -> str:
    licence_reference = licence_reference.split("/", 1)[1]
    return licence_reference.replace("/", "")

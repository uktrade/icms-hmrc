from mail.enums import SourceEnum
from mail.libraries.helpers import get_good_id, get_licence_id, get_action
from mail.models import LicenceIdMapping, TransactionMapping, UsageUpdate


def split_edi_data_by_id(usage_data, usage_update: UsageUpdate = None) -> (list, list):
    lines = usage_data.split("\n")
    spire_blocks = []
    lite_blocks = []
    block = []
    licence_owner = None
    licence_id = None
    transaction_id = None
    for line in lines:
        if "licenceUsage" in line and "end" not in line:
            licence_id = line.split("\\")[4]
            licence_owner = id_owner(licence_id)
            transaction_id = line.split("\\")[2]

        data_line = line.split("\\", 1)[1]
        block.append(data_line)

        if usage_update:
            if licence_owner == SourceEnum.LITE and "line" in data_line and "end" not in data_line:
                line_number = int(data_line.split("\\")[1])
                TransactionMapping.objects.get_or_create(
                    line_number=line_number,
                    usage_update=usage_update,
                    licence_reference=licence_id,
                    usage_transaction=transaction_id,
                )

            if (
                licence_owner == SourceEnum.LITE
                and not TransactionMapping.objects.filter(usage_transaction=transaction_id).exists()
                and "end\\licenceUsage" in line
            ):
                TransactionMapping.objects.get_or_create(
                    line_number=None,
                    usage_update=usage_update,
                    licence_reference=licence_id,
                    usage_transaction=transaction_id,
                )

        if "fileTrailer" in line:
            spire_blocks.append(block)
            break
        if "fileHeader" in line:
            spire_blocks.append(block)
            block = []

        if "licenceUsage" in line and "end" in line:
            if licence_owner == SourceEnum.SPIRE:
                spire_blocks.append(block)
            else:
                lite_blocks.append(block)
            block = []

    return spire_blocks, lite_blocks


def build_edifact_file_from_data_blocks(data_blocks: list) -> str:
    spire_file = ""
    i = 1
    for block in data_blocks:
        for line in block:
            spire_file += str(i) + "\\" + line + "\n"
            i += 1

    spire_file = spire_file[:-1]
    return spire_file


def build_json_payload_from_data_blocks(data_blocks: list) -> dict:
    payload = []
    licence_reference = None

    for block in data_blocks:
        licence_payload = {
            "id": "",
            "action": "",
            "completion_date": "",
            "goods": [],
        }

        for line in block:
            good_payload = {
                "id": "",
                "usage": "",
                "value": "",
                "currency": "",
            }

            line_array = line.split("\\")
            if "licenceUsage" in line and "end" not in line:
                licence_reference = line_array[3]
                action = line_array[4]
                licence_payload["action"] = get_action(action)
                if not action == "O" and len(line_array) >= 6:
                    licence_payload["completion_date"] = line_array[5]
                licence_payload["id"] = get_licence_id(licence_reference)

            if "line" == line_array[0]:

                good_payload["id"] = get_good_id(line_number=line_array[1], licence_reference=licence_reference)
                good_payload["usage"] = line_array[2]
                good_payload["value"] = line_array[3]
                if len(line_array) == 5:
                    good_payload["currency"] = line_array[4]

                licence_payload["goods"].append(good_payload)

        payload.append(licence_payload)

    return {"licences": payload}


def id_owner(licence_reference) -> str:
    if LicenceIdMapping.objects.filter(reference=licence_reference).exists():
        return SourceEnum.LITE
    else:
        return SourceEnum.SPIRE

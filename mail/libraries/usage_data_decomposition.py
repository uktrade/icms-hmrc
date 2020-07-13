from mail.enums import SourceEnum
from mail.libraries.helpers import get_good_id, get_licence_id
from mail.models import LicenceIdMapping, TransactionMapping, UsageUpdate


def split_edi_data_by_id(usage_data, usage_update: UsageUpdate = None):
    lines = usage_data.split("\n")
    spire_blocks = []
    lite_blocks = []
    block = []
    licence_owner = None
    licence_id = None
    transaction_id = None
    for line in lines:
        if "licenceUsage" in line and "end" not in line:
            licence_id = line.split(r"\{}".format(""))[4]
            licence_owner = id_owner(licence_id)
            transaction_id = line.split(r"\{}".format(""))[2]

        data_line = line.split(r"\{}".format(""), 1)[1]
        block.append(data_line)

        if usage_update and licence_owner == SourceEnum.LITE and "line" in data_line and "end" not in data_line:
            line_number = int(data_line.split("\\")[1])
            TransactionMapping.objects.get_or_create(
                line_number=line_number,
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


def build_edifact_file_from_data_blocks(data_blocks: list):
    spire_file = ""
    i = 1
    for block in data_blocks:
        for line in block:
            spire_file += str(i) + "\\" + line + "\n"
            i += 1

    spire_file = spire_file[:-1]
    return spire_file


# Keys for good payload (usage line)
# """
# [line number (some int)] = -1 <- inaccessible
# [line start (always usage)] = 0
# [usage_type] = 1
# [declaration-ucr] = 2
# [declaration-part-number] = 3
# [control-date] = 4
# [quantity-used] = 5
# [value-used] = 6
# [trader-id / TURN] = 7
# [claim-ref] = 8
# [origin-country (not used for exports)] = 9
# [customs-mic] = 10
# [customs-message] = 11
# [consignee-name] = 12
# """
# Sample block
# """
# [
#     "licenceUsage\\LU04148/00005\\insert\\GBOGE2011/56789\\O\\",
#     "line\\1\\0\\0\\",
#     "usage\\O\\9GB000004988000-4750437112345\\G\\20190111\\0\\0\\\\000104\\\\\\\\",
#     "usage\\O\\9GB000004988000-4750436912345\\Y\\20190111\\0\\0\\\\000104\\\\\\\\",
#     "end\\line\\4",
#     "end\\licenceUsage\\6",
# ]
# """


def build_json_payload_from_data_blocks(data_blocks: list):
    payload = []

    for block in data_blocks:
        licence_payload = {
            "id": "",
            "goods": [],
        }

        for line in block:
            good_payload = {
                "id": "",
                "usage": "",
                "value": "",
                "currency": "",
            }

            if "licenceUsage" in line and "end" not in line:
                licence_reference = line.split("\\")[3]
                licence_payload["id"] = get_licence_id(licence_reference)

            line_array = line.split("\\")
            if "line" == line_array[0]:

                good_payload["id"] = get_good_id(line_number=line_array[1], licence_reference=licence_reference)
                good_payload["usage"] = line_array[2]
                good_payload["value"] = line_array[3]
                if len(line_array) == 5:
                    good_payload["currency"] = line_array[4]

                licence_payload["goods"].append(good_payload)

        payload.append(licence_payload)

    return {"licences": payload}


def id_owner(licence_reference):
    if LicenceIdMapping.objects.filter(reference=licence_reference).exists():
        return SourceEnum.LITE
    else:
        return SourceEnum.SPIRE

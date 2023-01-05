from mail.enums import SourceEnum
from mail.models import LicenceIdMapping, TransactionMapping, UsageData


def split_edi_data_by_id(data, usage_data: UsageData = None) -> (list, list):
    lines = data.split("\n")
    spire_blocks = []
    lite_blocks = []
    block = []
    licence_owner = None
    licence_id = None
    transaction_id = None
    for line in lines:
        line = line.strip()
        if "licenceUsage" in line and "end" not in line:
            licence_id = line.split("\\")[4]
            licence_owner = id_owner(licence_id)
            transaction_id = line.split("\\")[2]

        data_line = line.split("\\", 1)[1]
        block.append(data_line)

        if usage_data:
            if licence_owner == SourceEnum.LITE and "line" in data_line and "end" not in data_line:
                line_number = int(data_line.split("\\")[1])
                TransactionMapping.objects.get_or_create(
                    line_number=line_number,
                    usage_data=usage_data,
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
                    usage_data=usage_data,
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


def id_owner(licence_reference) -> str:
    if LicenceIdMapping.objects.filter(reference=licence_reference).exists():
        return SourceEnum.LITE
    else:
        return SourceEnum.SPIRE

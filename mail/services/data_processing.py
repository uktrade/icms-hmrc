from mail.dtos import EmailMessageDto
from mail.services.helpers import convert_sender_to_source, process_attachment
from mail.models import LicenseUpdate
from mail.serializers import LicenseUpdateSerializer, InvalidEmailSerializer


def process_and_save_email_message(dto: EmailMessageDto):
    data = convert_dto_data_for_serialization(dto)

    serializer = LicenseUpdateSerializer(data=data)

    if serializer.is_valid():
        serializer.save()
        return True
    else:
        data["serializer_errors"] = str(serializer.errors)
        serializer = InvalidEmailSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
    return False


def convert_dto_data_for_serialization(dto: EmailMessageDto):
    data = {}
    last_hmrc_number = LicenseUpdate.objects.last().hmrc_run_number
    data["hmrc_run_number"] = (
        last_hmrc_number + 1 if last_hmrc_number != 99999 else 0
    )  # TODO: Extra logic to generalise
    data["source_run_number"] = dto.run_number

    data["edi_filename"], data["edi_data"] = process_attachment(dto.attachment)

    data["extract_type"] = "insert"  # TODO: extract from data
    data[
        "license_id"
    ] = "00000000-0000-0000-0000-000000000001"  # TODO: extract from data
    data["source"] = convert_sender_to_source(dto.sender)
    data["raw_data"] = dto.raw_data

    return data


def collect_and_send_data_to_dto():
    # determine run_number to use
    # get data out
    # return dto
    return True

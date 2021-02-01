import logging

from mail.libraries.helpers import get_extract_type
from mail.libraries.data_processors import convert_dto_data_for_serialization
from mock_hmrc import models, enums


def update_retrieved_email_status(dto, status):
    data = {"message_id": dto.message_id, "sender": dto.sender, "status": status}
    models.RetrievedMail.objects.get_or_create(**data)


def save_hmrc_email_message_data(dto):
    extract_type = get_extract_type(dto.subject)
    if not extract_type:
        update_retrieved_email_status(dto, enums.RetrievedEmailStatusEnum.INVALID)
        logging.info(f"Extract type not supported ({dto.subject}), skipping")
        return None

    data = convert_dto_data_for_serialization(dto, extract_type)

    # ensure there is run number
    if data["licence_data"]["source_run_number"] is None:
        logging.error("Invalid email received")
        update_retrieved_email_status(dto, enums.RetrievedEmailStatusEnum.INVALID)
        return None

    source_run_number = data["licence_data"]["source_run_number"]
    try:
        hmrc_mail = models.HmrcMail.objects.get(extract_type=extract_type, source_run_number=source_run_number)
    except models.HmrcMail.DoesNotExist:
        hmrc_mail = models.HmrcMail.objects.create(
            extract_type=extract_type,
            source_run_number=data["licence_data"]["source_run_number"],
            source=data["licence_data"]["source"],
            edi_filename=data["edi_filename"],
            edi_data=data["edi_data"],
            licence_ids=data["licence_data"]["licence_ids"],
        )
        update_retrieved_email_status(dto, enums.RetrievedEmailStatusEnum.VALID)

    return hmrc_mail

import logging

from django.conf import settings

from mail.constants import VALID_SENDERS
from mail.enums import ReceptionStatusEnum, SourceEnum
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import (
    convert_sender_to_source,
    get_licence_ids,
    new_hmrc_run_number,
    new_spire_run_number,
    process_attachment,
)


def convert_data_for_licence_data(dto: EmailMessageDto) -> dict:
    source = convert_sender_to_source(dto.sender)

    logging.info(f"Email sender ({dto.sender}) is determined as coming from {source}")

    data = {"licence_data": {}}
    data["licence_data"]["source"] = source
    data["licence_data"]["hmrc_run_number"] = (
        new_hmrc_run_number(int(dto.run_number)) if convert_sender_to_source(dto.sender) in VALID_SENDERS else None
    )
    data["licence_data"]["source_run_number"] = dto.run_number
    if source == SourceEnum.SPIRE:
        data["edi_filename"], data["edi_data"] = process_attachment(dto.attachment)
    else:
        data["edi_filename"] = dto.attachment[0]
        data["edi_data"] = dto.attachment[1]

    edi_data = data["edi_data"]
    if isinstance(edi_data, bytes):
        edi_data = edi_data.decode(settings.DEFAULT_ENCODING)
    data["licence_data"]["licence_ids"] = get_licence_ids(edi_data)
    _log_result(data)
    return data


def convert_data_for_licence_data_reply(dto: EmailMessageDto) -> dict:
    file_name, file_data = process_attachment(dto.attachment)
    data = {
        "response_filename": file_name,
        "response_data": file_data,
        "status": ReceptionStatusEnum.REPLY_RECEIVED,
        "response_subject": file_name,
    }
    _log_result(data)
    return data


def convert_data_for_usage_data(dto: EmailMessageDto) -> dict:
    data = {
        "usage_data": {},
        "edi_filename": process_attachment(dto.attachment)[0],
        "edi_data": process_attachment(dto.attachment)[1],
    }
    data["usage_data"]["spire_run_number"] = (
        new_spire_run_number(int(dto.run_number)) if convert_sender_to_source(dto.sender) in VALID_SENDERS else None
    )
    data["usage_data"]["hmrc_run_number"] = dto.run_number
    data["usage_data"]["licence_ids"] = get_licence_ids(data["edi_data"])
    return data


def convert_data_for_usage_data_reply(dto: EmailMessageDto) -> dict:
    file_name, file_data = process_attachment(dto.attachment)
    data = {
        "response_filename": file_name,
        "response_data": file_data,
        "status": ReceptionStatusEnum.REPLY_RECEIVED,
        "response_subject": file_name,
    }
    return data


def _log_result(data):
    output = ""
    for k, v in data.items():
        output += "{}->[{}] ".format(k, str(v))
    logging.info(output)

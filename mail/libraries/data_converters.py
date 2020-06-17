import logging

from mail.constants import VALID_SENDERS
from mail.enums import ReceptionStatusEnum, SourceEnum
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import (
    convert_sender_to_source,
    new_hmrc_run_number,
    process_attachment,
    get_licence_ids,
    new_spire_run_number,
)


def convert_data_for_licence_update(dto: EmailMessageDto) -> dict:
    source = convert_sender_to_source(dto.sender)
    data = {"licence_update": {}}
    data["licence_update"]["source"] = source
    data["licence_update"]["hmrc_run_number"] = (
        new_hmrc_run_number(int(dto.run_number)) if convert_sender_to_source(dto.sender) in VALID_SENDERS else None
    )
    data["licence_update"]["source_run_number"] = dto.run_number
    if source == SourceEnum.SPIRE:
        data["edi_filename"], data["edi_data"] = process_attachment(dto.attachment)
    else:
        data["edi_filename"] = dto.attachment[0]
        data["edi_data"] = dto.attachment[1]

    data["licence_update"]["licence_ids"] = get_licence_ids(data["edi_data"])
    _log_result(data)
    return data


def convert_data_for_licence_update_reply(dto: EmailMessageDto) -> dict:
    file_name, file_data = process_attachment(dto.attachment)
    data = {
        "response_filename": file_name,
        "response_data": file_data,
        "status": ReceptionStatusEnum.REPLY_RECEIVED,
        "response_subject": file_name,
    }
    _log_result(data)
    return data


def convert_data_for_usage_update(dto: EmailMessageDto) -> dict:
    data = {
        "usage_update": {},
        "edi_filename": process_attachment(dto.attachment)[0],
        "edi_data": process_attachment(dto.attachment)[1],
    }
    data["usage_update"]["spire_run_number"] = (
        new_spire_run_number(int(dto.run_number)) if convert_sender_to_source(dto.sender) in VALID_SENDERS else None
    )
    data["usage_update"]["hmrc_run_number"] = dto.run_number
    data["usage_update"]["licence_ids"] = get_licence_ids(data["edi_data"])
    return data


def convert_data_for_usage_update_reply(dto: EmailMessageDto) -> dict:
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
    logging.debug(output)

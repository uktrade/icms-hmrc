import json
import logging

from django.conf import settings
from django.utils import timezone

from mail.enums import ExtractTypeEnum
from mail.libraries.data_processors import convert_dto_data_for_serialization
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import get_extract_type
from mail.libraries.routing_controller import get_mock_hmrc_mailserver, send
from mock_hmrc import enums, models

MOCK_HMRC_SUPPORTED_EXTRACT_TYPES = [ExtractTypeEnum.LICENCE_DATA]


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

    hmrc_mail, _ = models.HmrcMail.objects.get_or_create(
        extract_type=extract_type,
        source_run_number=data["licence_data"]["source_run_number"],
        defaults={
            "source": data["licence_data"]["source"],
            "edi_filename": data["edi_filename"],
            "edi_data": data["edi_data"],
            "licence_ids": data["licence_data"]["licence_ids"],
        },
    )
    update_retrieved_email_status(dto, enums.RetrievedEmailStatusEnum.VALID)

    return hmrc_mail


def build_reply_pending_filename(filename):
    reply_identifier = ""
    filename = filename.split("_")
    extract_identifier = filename[3]

    if extract_identifier == "licenceData":
        reply_identifier = "licenceReply"

    # provide default value if it is unknown
    if reply_identifier == "":
        reply_identifier = "licenceUnknown"

    filename[3] = reply_identifier
    reply_filename = "_".join(filename)

    return reply_filename


def build_reply_pending_file_data(mail):
    """
    Builds a reply file that looks like an actual reply from HMRC

    Since we are simulating this only some of the cases are included.
    Eg rejected and error cases are not considered.
    """
    line_num = 1
    reply_created_time = timezone.localtime().strftime("%Y%m%d%H%M")
    data = []
    data.append(f"{line_num}\\fileHeader\\CHIEF\\SPIRE\\licenceReply\\{reply_created_time}\\{mail.source_run_number}")
    accepted_ids = json.loads(mail.licence_ids)
    for index, id in enumerate(accepted_ids, start=1):
        line_num += index
        data.append(f"{line_num}\\accepted\\{id}")

    data.append(f"{line_num}\\fileTrailer\\{len(accepted_ids)}\\0\\0")
    file_data = "\n".join(data)

    return file_data


def build_reply_mail_message_dto(mail) -> EmailMessageDto:
    if mail.extract_type not in MOCK_HMRC_SUPPORTED_EXTRACT_TYPES:
        return None

    sender = settings.MOCK_HMRC_EMAIL_USER
    receiver = settings.SPIRE_STANDIN_EMAIL_USER
    attachment = [
        build_reply_pending_filename(mail.edi_filename),
        build_reply_pending_file_data(mail),
    ]

    return EmailMessageDto(
        run_number=mail.source_run_number,
        sender=sender,
        receiver=receiver,
        subject=attachment[0],
        body=None,
        attachment=attachment,
        raw_data=None,
    )


def to_email_message_dto_from(hmrc_mail):
    if hmrc_mail.status == enums.HmrcMailStatusEnum.ACCEPTED:
        return build_reply_mail_message_dto(hmrc_mail)

    return None


def send_reply(email):
    message_to_send = to_email_message_dto_from(email)
    if message_to_send:
        server = get_mock_hmrc_mailserver()
        send(server, message_to_send)
        email.status = enums.HmrcMailStatusEnum.REPLIED
        email.save()

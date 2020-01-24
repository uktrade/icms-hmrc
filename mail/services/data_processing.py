import threading

from django.utils import timezone

from conf.constants import VALID_SENDERS
from conf.settings import SYSTEM_INSTANCE_UUID, LOCK_INTERVAL
from mail.dtos import EmailMessageDto
from mail.models import LicenceUpdate, Mail
from mail.serializers import InvalidEmailSerializer, LicenceUpdateMailSerializer
from mail.services.helpers import (
    convert_sender_to_source,
    process_attachment,
    new_hmrc_run_number,
    convert_source_to_sender,
    get_extract_type,
    get_licence_ids,
)


def process_and_save_email_message(dto: EmailMessageDto):
    data = convert_dto_data_for_serialization(dto)

    serializer = LicenceUpdateMailSerializer(data=data)

    if serializer.is_valid():
        mail = serializer.save()
        return mail
    else:
        data["serializer_errors"] = str(serializer.errors)
        serializer = InvalidEmailSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
    return False


def convert_dto_data_for_serialization(dto: EmailMessageDto):
    data = {"licence_update": {}}
    data["licence_update"]["source"] = convert_sender_to_source(dto.sender)
    data["licence_update"]["hmrc_run_number"] = (
        new_hmrc_run_number(dto.run_number)
        if convert_sender_to_source(dto.sender) in VALID_SENDERS
        else None
    )
    data["licence_update"]["source_run_number"] = dto.run_number
    data["edi_filename"], data["edi_data"] = process_attachment(dto.attachment)
    data["extract_type"] = get_extract_type(dto.subject)
    data["licence_update"]["license_ids"] = get_licence_ids(data["edi_data"])
    data["raw_data"] = dto.raw_data
    return data


def to_email_message_dto_from(mail):
    licence_update = LicenceUpdate.objects.get(mail=mail)
    dto = EmailMessageDto(
        run_number=licence_update.hmrc_run_number,
        sender=convert_source_to_sender(licence_update.source),
        receiver="HMRC",
        body="",
        subject=mail.edi_filename,
        attachment=[mail.edi_filename, mail.edi_data.encode("ascii", "replace")],
        raw_data=None,
    )
    return dto


def lock_db_for_sending_transaction(mail):
    mail.refresh_from_db()
    previous_locking_process_id = mail.currently_processed_by
    if (
        not previous_locking_process_id
        or (timezone.now() - mail.currently_processing_at).total_seconds()
        > LOCK_INTERVAL
    ):
        _mail = Mail.objects.select_for_update().get(id=mail.id)
        if _mail.currently_processed_by != previous_locking_process_id:
            return
        _mail.currently_processed_by = (
            str(SYSTEM_INSTANCE_UUID) + "-" + str(threading.currentThread().ident)
        )
        _mail.set_time()
        _mail.save()

        return True

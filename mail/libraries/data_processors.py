import logging
import threading

from django.db import transaction
from django.utils import timezone

from conf.settings import SYSTEM_INSTANCE_UUID, LOCK_INTERVAL
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.libraries.builders import build_request_mail_message_dto, build_reply_mail_message_dto
from mail.libraries.data_converters import (
    convert_data_for_licence_update,
    convert_data_for_licence_update_reply,
    convert_data_for_usage_update,
    convert_data_for_usage_update_reply,
)
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import (
    process_attachment,
    get_extract_type,
)
from mail.libraries.mailbox_service import find_mail_of
from mail.models import LicenceUpdate, Mail, UsageUpdate
from mail.serializers import (
    LicenceUpdateMailSerializer,
    UpdateResponseSerializer,
    UsageUpdateMailSerializer,
)


def serialize_email_message(dto: EmailMessageDto) -> Mail or None:
    extract_type = get_extract_type(dto.subject)
    if not extract_type:
        return

    instance = get_mail_instance(extract_type, dto.run_number)
    if not instance and extract_type in [ExtractTypeEnum.LICENCE_REPLY, ExtractTypeEnum.USAGE_REPLY]:
        return

    partial = True if instance else False
    data = convert_dto_data_for_serialization(dto, extract_type)
    serializer = get_serializer_for_dto(extract_type)
    serializer = serializer(instance=instance, data=data, partial=partial)

    if not serializer.is_valid():
        logging.error(f"Failed to serialize email -> {serializer.errors}")
        return

    _mail = serializer.save()
    if data["extract_type"] in ["licence_reply", "usage_reply"]:
        _mail.set_response_date_time()

    logging.info("Successfully serialized email")

    return _mail


def convert_dto_data_for_serialization(dto: EmailMessageDto, extract_type) -> dict:
    """
    Based on given mail message dto, prepare data for mail serialization.
    :param dto: the dto to be used
    :return: new dto for different extract type; corresponding Serializer;
            and existing mail if extract type is of reply. Both serializer and mail could be None
    """
    if extract_type == ExtractTypeEnum.LICENCE_UPDATE:
        data = convert_data_for_licence_update(dto)
    elif extract_type == ExtractTypeEnum.LICENCE_REPLY:
        data = convert_data_for_licence_update_reply(dto)
    elif extract_type == ExtractTypeEnum.USAGE_UPDATE:
        data = convert_data_for_usage_update(dto)
    elif extract_type == ExtractTypeEnum.USAGE_REPLY:
        data = convert_data_for_usage_update_reply(dto)
    else:
        # todo raise ValueError here
        filename, filedata = process_attachment(dto.attachment)
        data = {
            "edi_filename": filename,
            "edi_data": filedata,
        }

    data["extract_type"] = extract_type
    data["raw_data"] = dto.raw_data

    return data


def get_serializer_for_dto(extract_type):
    serializer = None
    if extract_type == ExtractTypeEnum.LICENCE_UPDATE:
        serializer = LicenceUpdateMailSerializer
    elif extract_type == ExtractTypeEnum.LICENCE_REPLY:
        serializer = UpdateResponseSerializer
    elif extract_type == ExtractTypeEnum.USAGE_UPDATE:
        serializer = UsageUpdateMailSerializer
    elif extract_type == ExtractTypeEnum.USAGE_REPLY:
        serializer = UpdateResponseSerializer

    return serializer


def get_mail_instance(extract_type, run_number) -> Mail or None:
    if extract_type == ExtractTypeEnum.LICENCE_REPLY:
        last_email = LicenceUpdate.objects.filter(hmrc_run_number=run_number).last()

        if last_email and last_email.mail.status in [
            ReceptionStatusEnum.REPLY_SENT,
            ReceptionStatusEnum.REPLY_RECEIVED,
        ]:
            logging.info("Licence update reply has already been processed")
            return
        return find_mail_of(ExtractTypeEnum.LICENCE_UPDATE, ReceptionStatusEnum.REPLY_PENDING)
    elif extract_type == ExtractTypeEnum.USAGE_REPLY:
        last_email = UsageUpdate.objects.filter(spire_run_number=run_number).last()

        if last_email and last_email.mail.status in [
            ReceptionStatusEnum.REPLY_SENT,
            ReceptionStatusEnum.REPLY_RECEIVED,
        ]:
            logging.info("Usage update reply has already been processed")
            return
        return find_mail_of(ExtractTypeEnum.USAGE_UPDATE, ReceptionStatusEnum.REPLY_PENDING)


def to_email_message_dto_from(mail: Mail) -> EmailMessageDto:
    _check_and_raise_error(mail, "Invalid mail object received!")
    logging.debug(
        f"converting mail [{mail.id}] with status [{mail.status}] extract_type [{mail.extract_type}] "
        f"to EmailMessageDto"
    )
    if mail.status == ReceptionStatusEnum.PENDING:
        logging.debug(f"building request mail [{mail.id}] message dto from [{mail.status}] mail status")
        return build_request_mail_message_dto(mail)
    elif mail.status == ReceptionStatusEnum.REPLY_RECEIVED:
        logging.debug(f"building reply mail [{mail.id}] message dto from [{mail.status}] mail status")
        return build_reply_mail_message_dto(mail)
    logging.warning(f"Unexpected mail [{mail.id}] with status [{mail.status}] while converting to EmailMessageDto")


def lock_db_for_sending_transaction(mail: Mail) -> bool:
    mail.refresh_from_db()
    previous_locking_process_id = mail.currently_processed_by
    if (
        not previous_locking_process_id
        or (timezone.now() - mail.currently_processing_at).total_seconds() > LOCK_INTERVAL
    ):
        with transaction.atomic():
            _mail = Mail.objects.select_for_update().get(id=mail.id)
            if _mail.currently_processed_by != previous_locking_process_id:
                return False
            _mail.currently_processed_by = str(SYSTEM_INSTANCE_UUID) + "-" + str(threading.currentThread().ident)
            _mail.set_locking_time()
            _mail.save()

            return True


def _check_and_raise_error(obj, error_msg: str):
    if obj is None:
        raise ValueError(error_msg)

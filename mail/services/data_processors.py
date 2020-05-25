import logging
import threading

from django.db import transaction
from django.utils import timezone

from conf.settings import (
    SYSTEM_INSTANCE_UUID,
    LOCK_INTERVAL,
    HMRC_ADDRESS,
    SPIRE_ADDRESS,
)
from mail.dtos import EmailMessageDto
from mail.enums import ExtractTypeEnum, ReceptionStatusEnum
from mail.models import LicenceUpdate, Mail, UsageUpdate
from mail.serializers import (
    InvalidEmailSerializer,
    LicenceUpdateMailSerializer,
    UpdateResponseSerializer,
    UsageUpdateMailSerializer,
)
from mail.services.data_converters import (
    convert_data_for_licence_update,
    convert_data_for_licence_update_reply,
    convert_data_for_usage_update,
    convert_data_for_usage_update_reply,
)
from mail.services.helpers import (
    process_attachment,
    get_extract_type,
    get_all_serializer_errors_for_mail,
)
from mail.services.logging_decorator import lite_log
from mail.services.MailboxService import MailboxService

logger = logging.getLogger(__name__)


def serialize_email_message(dto: EmailMessageDto) -> Mail:
    extract_type = get_extract_type(dto.subject)
    lite_log(logger, logging.INFO, f"Email type identified as {extract_type}")

    data = convert_dto_data_for_serialization(dto, extract_type)
    serializer = get_serializer_for_dto(extract_type)
    instance = get_mail_instance(extract_type)

    logger.debug(
        _check_and_return_msg(
            {"data": data, "serializer": serializer, "mail": instance,}
        )
    )

    partial = True if instance else False
    if serializer:
        serializer = serializer(instance=instance, data=data, partial=partial)
        lite_log(
            logger,
            logging.DEBUG,
            "{} initialized with partial [{}]".format(
                type(serializer).__name__, partial
            ),
        )
    if serializer and serializer.is_valid():
        _mail = serializer.save()
        lite_log(logger, logging.DEBUG, "{} saved".format(type(serializer).__name__))
        if data["extract_type"] in ["licence_reply", "usage_reply"]:
            _mail.set_response_date_time()
            lite_log(
                logger,
                logging.DEBUG,
                "mail response datetime updated. status {}".format(_mail.status),
            )
        return _mail
    else:
        data["serializer_errors"] = get_all_serializer_errors_for_mail(data)
        lite_log(logger, logging.ERROR, data["serializer_errors"])
        serializer = InvalidEmailSerializer(data=data)
        if serializer.is_valid():
            serializer.save()

    return False


def convert_dto_data_for_serialization(dto: EmailMessageDto, extract_type):
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


def get_mail_instance(extract_type):
    mail = None
    if extract_type == ExtractTypeEnum.LICENCE_REPLY:
        mail = MailboxService.find_mail_of(
            ExtractTypeEnum.LICENCE_UPDATE, ReceptionStatusEnum.REPLY_PENDING
        )
    elif extract_type == ExtractTypeEnum.USAGE_REPLY:
        mail = MailboxService.find_mail_of(
            ExtractTypeEnum.USAGE_UPDATE, ReceptionStatusEnum.REPLY_PENDING
        )
    return mail


def to_email_message_dto_from(mail):
    _check_and_raise_error(mail, "Invalid mail object received!")
    lite_log(
        logger,
        logging.DEBUG,
        f"converting mail with status {mail.status} extract_type [{mail.extract_type}] to EmailMessageDto",
    )
    if mail.status == ReceptionStatusEnum.PENDING:
        logger.debug(
            f"building request mail message dto from [{mail.status}] mail status"
        )
        return _build_request_mail_message_dto(mail)
    elif mail.status == ReceptionStatusEnum.REPLY_RECEIVED:
        logger.debug(
            f"building reply mail message dto from [{mail.status}] mail status"
        )
        return _build_reply_mail_message_dto(mail)
    raise ValueError(
        f"Unexpected mail with status: {mail.status} while converting to EmailMessageDto"
    )


def lock_db_for_sending_transaction(mail):
    mail.refresh_from_db()
    previous_locking_process_id = mail.currently_processed_by
    if (
        not previous_locking_process_id
        or (timezone.now() - mail.currently_processing_at).total_seconds()
        > LOCK_INTERVAL
    ):
        with transaction.atomic():
            _mail = Mail.objects.select_for_update().get(id=mail.id)
            if _mail.currently_processed_by != previous_locking_process_id:
                return
            _mail.currently_processed_by = (
                str(SYSTEM_INSTANCE_UUID) + "-" + str(threading.currentThread().ident)
            )
            _mail.set_locking_time()
            _mail.save()

            return True


def _build_request_mail_message_dto(mail):
    sender = SPIRE_ADDRESS
    receiver = HMRC_ADDRESS
    if mail.extract_type == ExtractTypeEnum.LICENCE_UPDATE:
        licence_update = LicenceUpdate.objects.get(mail=mail)
        run_number = licence_update.hmrc_run_number
    elif mail.extract_type == ExtractTypeEnum.USAGE_UPDATE:
        update = UsageUpdate.objects.get(mail=mail)
        run_number = update.spire_run_number
        sender = HMRC_ADDRESS
        receiver = SPIRE_ADDRESS

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        subject=mail.edi_filename,
        body=None,
        attachment=[mail.edi_filename, mail.edi_data],
        raw_data=None,
    )


def _build_reply_mail_message_dto(mail):
    sender = HMRC_ADDRESS
    receiver = SPIRE_ADDRESS
    if mail.extract_type == ExtractTypeEnum.LICENCE_UPDATE:
        licence_update = LicenceUpdate.objects.get(mail=mail)
        run_number = licence_update.source_run_number
    elif mail.extract_type == ExtractTypeEnum.USAGE_UPDATE:
        usage_update = UsageUpdate.objects.get(mail=mail)
        run_number = usage_update.spire_run_number
        sender = SPIRE_ADDRESS
        receiver = HMRC_ADDRESS

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        subject=mail.response_subject,
        body=None,
        attachment=[mail.response_filename, mail.response_data],
        raw_data=None,
    )


def _check_and_raise_error(obj, error_msg: str):
    if obj is None:
        raise ValueError(error_msg)


def _check_and_return_msg(dict_obj):
    output = ""
    for obj_name, obj in dict_obj.items():
        if obj:
            output += "{} is set. ".format(obj_name)
        else:
            output += "{} is None. ".format(obj_name)
    return output

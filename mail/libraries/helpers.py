import base64
import json
import logging
from email.message import Message
from email.parser import Parser
from json.decoder import JSONDecodeError

import sentry_sdk
from dateutil.parser import parse
from django.conf import settings

from mail import serializers
from mail.enums import ExtractTypeEnum, LicenceStatusEnum, ReceptionStatusEnum, SourceEnum, UnitMapping
from mail.libraries.email_message_dto import EmailMessageDto, HmrcEmailMessageDto
from mail.models import GoodIdMapping, LicenceData, LicenceIdMapping, Mail, UsageData

ALLOWED_FILE_MIMETYPES = ["application/octet-stream", "text/plain"]


logger = logging.getLogger(__name__)


def guess_charset(msg: Message) -> str:
    """
    Guest charset of given
    :param msg:
    :return:
    """
    charset = msg.get_charset()
    if charset is None:
        content_type = msg.get("Content-Type", "").lower()
        pos = content_type.find("charset=")
        if pos >= 0:
            charset = content_type[pos + 8 :].strip()
    return charset


def body_contents_of(msg: Message):
    """
    Retrive body contents of given message
    :param msg: a message object
    :return: body contents
    """
    if not isinstance(msg, Message):
        raise TypeError('Given param is not of type "email.message.Message"')

    if msg.is_multipart():
        parts = msg.get_payload()
        for _, part in enumerate(parts):
            return body_contents_of(part)
    if not msg.is_multipart():
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            content = msg.get_payload(decode=True)
            charset = guess_charset(msg)
            if charset:
                content = content.decode(charset)
            return content


def get_attachment(msg: Message):
    """
    Get file attachment from given mail message object.
    :param msg: a message object of email.message.Message
    :return: a tuple of file name and file data; none if there is no file attachment
    """
    for part in msg.walk():
        if part.get_content_type() in ALLOWED_FILE_MIMETYPES:
            name = part.get_filename()
            data = part.get_payload(decode=True)
            if name:
                return name, data
    logging.info("No attachment found")
    return None, None


def to_mail_message_dto(mail_data) -> EmailMessageDto:
    mail_contents = mail_data[1]
    contents = b"\r\n".join(mail_contents).decode(settings.DEFAULT_ENCODING)
    msg_obj = Parser().parsestr(contents)
    msg = body_contents_of(msg_obj)
    file_name, file_data = get_attachment(msg_obj)
    msg_date = parse(msg_obj.get("Date"))
    return EmailMessageDto(
        subject=msg_obj.get("Subject"),
        sender=msg_obj.get("From"),
        receiver=msg_obj.get("To"),
        date=msg_date,
        body=msg,
        attachment=[file_name, file_data],
        run_number=get_run_number(msg_obj.get("Subject")),
        raw_data=str(mail_data),
    )


def to_hmrc_mail_message_dto(message_id, mail_data) -> HmrcEmailMessageDto:
    mail_contents = mail_data[1]
    contents = b"\r\n".join(mail_contents).decode(settings.DEFAULT_ENCODING)
    msg_obj = Parser().parsestr(contents)
    msg = body_contents_of(msg_obj)
    file_name, file_data = get_attachment(msg_obj)
    return HmrcEmailMessageDto(
        message_id=message_id,
        subject=msg_obj.get("Subject"),
        sender=msg_obj.get("From"),
        receiver=msg_obj.get("To"),
        body=msg,
        attachment=[file_name, file_data],
        run_number=get_run_number(msg_obj.get("Subject")),
        raw_data=str(mail_data),
    )


def get_run_number(patterned_text: str) -> int:
    """
    Gets run-number from a patterned text: abc_xyz_nnn_yyy_1234_datetime.
    :returns found number; ValueError if it not found or is not a number
    """

    if patterned_text is None:
        raise ValueError("None received")

    try:
        split_str = patterned_text.split("_", 6)
        if len(split_str) != 6 or not split_str[4].isdigit():
            raise ValueError("Can not find valid run-number")
        return int(patterned_text.split("_", 6)[4])
    except Exception:  # noqa
        return 10000


def convert_sender_to_source(sender: str) -> str:
    if "<" in sender and ">" in sender:
        sender = sender.split("<")[1].split(">")[0]

    if sender == settings.SPIRE_ADDRESS:
        return SourceEnum.SPIRE
    elif sender == SourceEnum.LITE:
        return SourceEnum.LITE
    elif sender == settings.HMRC_ADDRESS:
        return SourceEnum.HMRC

    if sender in [settings.SPIRE_INCOMING_EMAIL_ADDRESS, settings.INCOMING_EMAIL_USER]:
        return SourceEnum.SPIRE

    return sender


def convert_source_to_sender(source) -> str:
    if source == SourceEnum.SPIRE:
        return settings.SPIRE_ADDRESS
    elif source == SourceEnum.LITE:
        return SourceEnum.LITE
    return source


def process_attachment(attachment):
    if len(attachment) != 2:
        logger.error(
            "Length of attachment is incorrect: attachment=%s",
            attachment,
            exc_info=True,
        )

        return "", ""

    file_name = attachment[0]
    file_data = attachment[1]
    file_data = file_data.decode("utf-8")

    logging.debug(f"attachment filename: {file_name}, filedata:\n{file_data}")
    return file_name, file_data


def new_hmrc_run_number(dto_run_number: int) -> int:
    last_update = LicenceData.objects.last()
    if last_update:
        dto_run_number = dto_run_number % 100000
        if not last_update.source_run_number == dto_run_number:
            return last_update.hmrc_run_number + 1 if last_update.hmrc_run_number != 99999 else 0
        else:
            return last_update.hmrc_run_number
    return dto_run_number


def new_spire_run_number(dto_run_number: int) -> int:
    last_usage_data = UsageData.objects.last()
    if last_usage_data:
        dto_run_number = dto_run_number % 100000
        if not last_usage_data.hmrc_run_number == dto_run_number:
            return last_usage_data.spire_run_number + 1 if last_usage_data.spire_run_number != 99999 else 0
        else:
            return last_usage_data.spire_run_number
    return dto_run_number


def get_extract_type(subject: str) -> str or None:
    for key, value in ExtractTypeEnum.email_keys:
        if key in str(subject):
            return value
    return None


def get_licence_ids(file_body) -> str:
    ids = []
    file_body = file_body.strip(" ")
    lines = file_body.split("\n")
    for line in lines:
        if line and "licence" in line.split("\\")[1]:
            ids.append(line.split("\\")[4])
    logging.debug(f"licence ids in the file: {ids}")
    return json.dumps(ids)


def read_file(file_path: str, mode: str = "r", encoding: str = None):
    with open(file_path, mode=mode, encoding=encoding) as f:
        return f.read()


def decode(data, char_set: str):
    return data.decode(char_set) if isinstance(data, bytes) else data


def b64encode(byte_text: str):
    return base64.b64encode(byte_text)


def b64decode(b64encoded_text: str):
    return base64.b64decode(b64encoded_text)


def map_unit(data: dict, g: int) -> dict:
    unit = data["goods"][g]["unit"]
    data["goods"][g]["unit"] = UnitMapping.convert(unit)
    return data


def select_email_for_sending() -> Mail or None:
    logging.info("Selecting email to send")

    reply_received = Mail.objects.filter(status=ReceptionStatusEnum.REPLY_RECEIVED).first()
    if reply_received:
        if reply_received.extract_type == ExtractTypeEnum.USAGE_DATA:
            usage_data = UsageData.objects.get(mail=reply_received)
            if usage_data.has_lite_data and not usage_data.lite_sent_at:
                return
        return reply_received

    reply_pending = Mail.objects.filter(status=ReceptionStatusEnum.REPLY_PENDING).first()
    if reply_pending:
        if reply_pending.extract_type == ExtractTypeEnum.USAGE_DATA:
            usage_data = UsageData.objects.get(mail=reply_pending)
            if not usage_data.has_spire_data:
                return reply_pending
        logging.info("Email currently in flight")
        return

    pending = Mail.objects.filter(status=ReceptionStatusEnum.PENDING).first()
    if pending:
        return pending

    logging.info("No emails to send")
    return


def check_for_pending_messages():
    """
    Checks for any licenceData or usageData messages with "pending" status

    We send one licenceData mail and wait for the reply before sending the next one.
    However HMRC sends us usageData mails along with replies. In a given polling interval if we get
    licenceReply and usageData at the same time then we process both of them (serialize and save)
    but we only send one of them. The other one remains with "pending" status.
    There is a deadlock situation if the pending mail is of type licenceData because in the next polling
    interval there won't be any new emails and we exit early. The pending mail gets stuck in the queue
    and is never sent to HMRC. Because of this we won't get reply also from HMRC and SPIRE won't send
    us the next mail and the queue gets blocked.

    To fix this we are going to look for pending mails when there are no new mails. Following the same
    order as they are created, if there is a pending licenceData mail (should not be more than one if present)
    then we send that otherwise if there is a pending usageData mails (can be multiple) we just
    send the oldest. Because this is repeated in each polling interval all the pending mails gets cleared
    and the queue gets unblocked.
    """

    ld_pending_count = Mail.objects.filter(
        extract_type=ExtractTypeEnum.LICENCE_DATA, status=ReceptionStatusEnum.PENDING
    ).count()
    if ld_pending_count and ld_pending_count > 1:
        raise Exception("More than 1 licenceData pending mails found")

    pending = Mail.objects.filter(status=ReceptionStatusEnum.PENDING).order_by("created_at").first()
    if pending:
        # check if we are waiting for reply for any licenceData mail sent previously
        # if yes then don't send this pending mail as we have to send only after receiving reply
        # usageData mails can be sent to SPIRE without any issues
        reply_pending = Mail.objects.filter(
            extract_type=ExtractTypeEnum.LICENCE_DATA, status=ReceptionStatusEnum.REPLY_PENDING
        )
        if reply_pending and pending.extract_type == ExtractTypeEnum.LICENCE_DATA:
            raise Exception("Received another licenceData mail while waiting for reply")

        return pending


def get_good_id(line_number, licence_reference) -> str or None:
    """
    Returns the LITE API Good ID or None (Good IDs for Open Licences are not mapped as they are not needed)
    """
    try:
        return str(GoodIdMapping.objects.get(line_number=line_number, licence_reference=licence_reference).lite_id)
    except Exception as exc:  # noqa
        return


def get_licence_id(licence_reference) -> str or None:
    try:
        return str(LicenceIdMapping.objects.get(reference=licence_reference).lite_id)
    except Exception as exc:  # noqa
        return


def get_licence_status(reference) -> str:
    if reference == "O":
        return LicenceStatusEnum.OPEN
    elif reference == "E":
        return LicenceStatusEnum.EXHAUST
    elif reference == "S":
        return LicenceStatusEnum.SURRENDER
    elif reference == "D":
        return LicenceStatusEnum.EXPIRE
    elif reference == "C":
        return LicenceStatusEnum.CANCEL


def get_country_id(country):
    try:
        if type(country) == dict:
            country_code = country["id"]
        else:
            country_code = json.loads(country)["id"]
        # skip territory code, if exists
        return country_code.split("-")[0]
    except (TypeError, JSONDecodeError):
        return country.split("-")[0]


def sort_dtos_by_date(input_dtos):
    return sorted(input_dtos, key=lambda d: d[0].date)


def log_to_sentry(message, extra=None, level="info"):
    extra = extra or {}
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level=level)


def get_licence_data_status():
    mail = (
        Mail.objects.filter(extract_type__in=[ExtractTypeEnum.LICENCE_DATA, ExtractTypeEnum.LICENCE_REPLY])
        .order_by("created_at")
        .last()
    )
    licence_data_qs = LicenceData.objects.filter(mail=mail)
    if not licence_data_qs:
        return {}

    licence_data = licence_data_qs.first()
    status = serializers.LicenceDataStatusSerializer(licence_data).data

    # usually we should receive reply in 20-30 min
    processing_time_min = status.get("processing_time")
    if mail.status == ReceptionStatusEnum.REPLY_PENDING:
        status["waiting_time"] = f"Reply waiting time {processing_time_min} min"
    elif mail.status == ReceptionStatusEnum.REPLY_SENT:
        status["round_trip_time"] = f"Total round trip time {processing_time_min} min"

    return status


def get_usage_data_status():
    mail = Mail.objects.filter(extract_type=ExtractTypeEnum.USAGE_DATA).order_by("created_at").last()
    usage_data_qs = UsageData.objects.filter(mail=mail)
    if not usage_data_qs:
        return {}

    usage_data = usage_data_qs.first()
    return serializers.UsageDataStatusSerializer(usage_data).data


def publish_queue_status():
    """
    Uses the last Licence data mail and Usage data to get the status of the queue.

    Since we shouldn't sent next licence data mail without receiving reply for the previous one
    checking the last mail is sufficient to detect any anamolies.
    """
    queue_status = {}
    queue_status["licence_data"] = get_licence_data_status()
    queue_status["usage_data"] = get_usage_data_status()

    ## In the increasing order of severity
    queue_state = "HEALTHY"
    extra_state = {}

    licence_data_status = queue_status.get("licence_data")
    if licence_data_status:
        processing_time = licence_data_status.get("processing_time")
        if "waiting_time" in licence_data_status and processing_time > 30:
            queue_state = "RESPONSE TIMEOUT"

        # we should only be waiting for reply for one licence data mail
        if licence_data_status["reply_pending_count"] > 1:
            queue_state = "REQUIRES ATTENTION"

        extra_state = {**queue_status["licence_data"]}

    if "usage_data" in queue_status:
        extra_state = {**extra_state, **queue_status["usage_data"]}

    log_to_sentry(f"Mail queue status: {queue_state} (see additional data below)", extra=extra_state)

import base64
import json
import logging
from email.message import Message
from email.parser import Parser

from django.utils.encoding import smart_text

from conf.settings import SPIRE_ADDRESS, HMRC_ADDRESS
from mail.enums import SourceEnum, ExtractTypeEnum, UnitMapping, ReceptionStatusEnum
from mail.libraries.email_message_dto import EmailMessageDto
from mail.models import LicenceUpdate, UsageUpdate, Mail, GoodIdMapping, LicenceIdMapping

ALLOWED_FILE_MIMETYPES = ["application/octet-stream", "text/plain"]


def guess_charset(msg: Message):
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
    contents = b"\r\n".join(mail_contents).decode("utf-8")
    msg_obj = Parser().parsestr(contents)
    msg = body_contents_of(msg_obj)
    file_name, file_data = get_attachment(msg_obj)
    return EmailMessageDto(
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
    if sender == SPIRE_ADDRESS:
        return SourceEnum.SPIRE
    elif sender == SourceEnum.LITE:
        return SourceEnum.LITE
    elif sender == HMRC_ADDRESS:
        return SourceEnum.HMRC
    return sender


def convert_source_to_sender(source) -> str:
    if source == SourceEnum.SPIRE:
        return SPIRE_ADDRESS
    elif source == SourceEnum.LITE:
        return SourceEnum.LITE
    return source


def process_attachment(attachment):
    file_name = ""
    file_data = ""

    if len(attachment) == 2:
        file_name = attachment[0]
        file_data = attachment[1]
        file_data = file_data.decode("utf-8")

    logging.debug(f"attachment filename: {file_name}, filedata:\n{file_data}")
    return file_name, file_data


def new_hmrc_run_number(dto_run_number: int):
    last_licence_update = LicenceUpdate.objects.last()
    if last_licence_update:
        dto_run_number = dto_run_number % 100000
        if not last_licence_update.source_run_number == dto_run_number:
            return last_licence_update.hmrc_run_number + 1 if last_licence_update.hmrc_run_number != 99999 else 0
        else:
            return last_licence_update.hmrc_run_number
    return dto_run_number


def new_spire_run_number(dto_run_number: int):
    last_usage_update = UsageUpdate.objects.last()
    if last_usage_update:
        dto_run_number = dto_run_number % 100000
        if not last_usage_update.hmrc_run_number == dto_run_number:
            return last_usage_update.spire_run_number + 1 if last_usage_update.spire_run_number != 99999 else 0
        else:
            return last_usage_update.spire_run_number
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
    logging.debug(f"license ids in the file: {ids}")
    return json.dumps(ids)


def read_file(file_path: str, mode: str = "r", encoding: str = None):
    _file = open(file_path, mode=mode, encoding=encoding)
    return _file.read()


def decode(data, char_set: str):
    return data.decode(char_set) if isinstance(data, bytes) else data


def to_smart_text(byte_str: str, encoding="ASCII"):
    return smart_text(byte_str, encoding=encoding)


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
        if reply_received.extract_type == ExtractTypeEnum.USAGE_UPDATE:
            usage_update = UsageUpdate.objects.get(mail=reply_received)
            if usage_update.has_lite_data and not usage_update.lite_sent_at:
                return
        return reply_received

    reply_pending = Mail.objects.filter(status=ReceptionStatusEnum.REPLY_PENDING).first()
    if reply_pending:
        if reply_pending.extract_type == ExtractTypeEnum.USAGE_UPDATE:
            usage_update = UsageUpdate.objects.get(mail=reply_pending)
            if not usage_update.has_spire_data:
                return reply_pending
        logging.info("Email currently in flight")
        return

    pending = Mail.objects.filter(status=ReceptionStatusEnum.PENDING).first()
    if pending:
        return pending

    logging.info("No emails to send")
    return


def get_good_id(line_number, licence_reference):
    try:
        return str(GoodIdMapping.objects.get(line_number=line_number, licence_reference=licence_reference).lite_id)
    except Exception as exc:  # noqa
        return


def get_licence_id(licence_reference):
    try:
        return str(LicenceIdMapping.objects.get(reference=licence_reference).lite_id)
    except Exception as exc:  # noqa
        return


def get_previous_licence_reference(reference):
    if ord(reference[-1]) == 97:
        if len(reference) >= 2 and reference[-2] == "/":
            return reference[0:-2]
        return reference[0:-1]
    else:
        return reference[0:-1] + chr(ord(reference[-1]) - 1)

import base64
import json
import logging
import string
from django.utils.encoding import smart_text
from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.parser import Parser

from conf.settings import SPIRE_ADDRESS, HMRC_ADDRESS
from mail.dtos import EmailMessageDto
from mail.enums import SourceEnum, ExtractTypeEnum
from mail.models import LicenceUpdate, UsageUpdate
from mail.serializers import LicenceUpdateMailSerializer, UsageUpdateMailSerializer
from mail.services.logging_decorator import lite_log

ALLOWED_FILE_MIMETYPES = ["application/octet-stream"]

logger = logging.getLogger(__name__)


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
    :return: a tuplet of file name and file data; none if there is no file attachment
    """
    for part in msg.walk():
        if part.get_content_type() in ALLOWED_FILE_MIMETYPES:
            name = part.get_filename()
            data = part.get_payload(decode=True)
            return name, data
    logging.info({"message": "liteolog hmrc", "attachment": "No attachment found"})
    return None, None


def to_mail_message_dto(mail_data: object):
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
        run_number=get_runnumber(msg_obj.get("Subject")),
        raw_data=str(mail_data),
    )


def get_runnumber(patterned_text: str):
    """Gets run-number from a patterned text: abc_xyz_nnn_yyy_1234_datetime.
    :returns found number; ValueError if it not found or is not a number
    """
    if patterned_text is None:
        raise ValueError("None received")

    split_str = patterned_text.split("_", 6)
    if len(split_str) != 6 or not split_str[4].isdigit():
        raise ValueError("Can not find valid run-number")
    return patterned_text.split("_", 6)[4]


def convert_sender_to_source(sender: string):
    if "<" in sender and ">" in sender:
        sender = sender.split("<")[1].split(">")[0]
    if sender == SPIRE_ADDRESS:
        return "SPIRE"
    elif sender == "test@lite.com":
        return "LITE"
    elif sender == HMRC_ADDRESS:
        return "HMRC"
    return sender


def convert_source_to_sender(source):
    if source == SourceEnum.SPIRE:
        return SPIRE_ADDRESS
    elif source == SourceEnum.LITE:
        return "test@lite.com"
    return source


def process_attachment(attachment):
    file_name = attachment[0] if attachment and attachment[0] is not None else ""
    file_data = attachment[1] if attachment and attachment[1] is not None else ""
    lite_log(
        logger,
        logging.DEBUG,
        f"attachment filename: {file_name}, filedata:\n{file_data}",
    )
    return file_name, file_data


def new_hmrc_run_number(dto_run_number: int):
    last_licence_update = LicenceUpdate.objects.last()
    if last_licence_update:
        dto_run_number = dto_run_number % 100000
        if not last_licence_update.source_run_number == dto_run_number:
            return (
                last_licence_update.hmrc_run_number + 1
                if last_licence_update.hmrc_run_number != 99999
                else 0
            )
        else:
            return last_licence_update.hmrc_run_number
    return dto_run_number


def new_spire_run_number(dto_run_number: int):
    last_usage_update = UsageUpdate.objects.last()
    if last_usage_update:
        dto_run_number = dto_run_number % 100000
        if not last_usage_update.hmrc_run_number == dto_run_number:
            return (
                last_usage_update.spire_run_number + 1
                if last_usage_update.spire_run_number != 99999
                else 0
            )
        else:
            return last_usage_update.spire_run_number
    return dto_run_number


def get_extract_type(subject: str):
    for key, value in ExtractTypeEnum.email_keys:
        if key in str(subject):
            return value
    return None


def get_licence_ids(file_body, b64_encoded=False):
    ids = []
    _file_body = to_smart_text(b64decode(file_body)) if b64_encoded else file_body
    lines = _file_body.split("\n")
    for line in lines:
        if ("licenceUsage" in line or "licenceUpdate" in line) and "end" not in line:
            ids.append(line.split("\\")[4])
    logger.debug(f"license ids in the file: {ids}")
    return json.dumps(ids)


def build_email_message(email_message_dto: EmailMessageDto):
    """Build mail message from EmailMessageDto.
    :param email_message_dto: the DTO object this mail message is built upon
    :return: a multipart message
    """
    _validate_dto(email_message_dto)

    multipart_msg = MIMEMultipart()
    multipart_msg["From"] = email_message_dto.sender
    multipart_msg["To"] = email_message_dto.receiver
    multipart_msg["Subject"] = email_message_dto.subject
    payload = MIMEApplication(email_message_dto.attachment[1])
    payload.set_payload(email_message_dto.attachment[1])
    payload.add_header(
        "Content-Disposition",
        "attachment; filename= %s" % email_message_dto.attachment[0],
    )
    multipart_msg.attach(payload)
    return multipart_msg


def _validate_dto(email_message_dto):
    if email_message_dto is None:
        raise TypeError("None email_message_dto received!")

    if email_message_dto.attachment is None:
        raise TypeError("None file attachment received!")


def get_all_serializer_errors_for_mail(data):
    errors = ""
    if not hasattr(data, "licence_update"):
        data["licence_update"] = {}
    if not hasattr(data, "usage_update"):
        data["usage_update"] = {}
    for serializer in [LicenceUpdateMailSerializer, UsageUpdateMailSerializer]:
        serializer = serializer(data=data)
        if not serializer.is_valid():
            errors += str(serializer.errors)
    return errors


def read_file(file_path: str):
    _file = open(file_path, "rb")
    return _file.read()


def decode(data, char_set: str):
    return data.decode(char_set) if isinstance(data, bytes) else data


def to_smart_text(byte_str: str, encoding="ASCII"):
    return smart_text(byte_str, encoding=encoding)


def b64encode(byte_text: str):
    return base64.b64encode(byte_text)


def b64decode(b64encoded_text: str):
    return base64.b64decode(b64encoded_text)

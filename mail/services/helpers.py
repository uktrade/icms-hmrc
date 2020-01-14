import string
from email.message import Message
from email.parser import Parser
from mail.dtos import EmailMessageDto

ALLOWED_FILE_MIMETYPES = ["application/octet-stream"]


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
        raw_data=mail_data,
    )


def get_runnumber(subject: str):
    """todo: """
    return "99"


def convert_sender_to_source(sender: string):
    if sender == "test@spire.com":
        return "SPIRE"
    elif sender == "test@lite.com":
        return "LITE"
    else:
        return sender


def process_attachment(attachment):
    try:
        edi_filename = attachment[0]
        edi_data = attachment[1]
        return edi_filename, str(edi_data)
    except IndexError:
        return "", ""

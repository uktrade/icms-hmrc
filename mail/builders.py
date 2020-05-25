from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mail.dtos import EmailMessageDto


def build_text_message(
    sender, receiver, body="Body_of_the_mail 2", file_path="/app/Pipfile"
):
    """build a message of `MineMultipart` with a text attachment and octet-stream payload.\n
        Todo: using a custom builder to build mail message
    """
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = "ILBDOTI_test_CHIEF_usageData_9876_201901130300"
    body = body
    msg.attach(MIMEText(body, "plain"))
    filename = "ILBDOTI_test_CHIEF_usageData_9876_201901130300"
    attachment = open(file_path, "rb")
    payload = MIMEBase("application", "octet-stream")
    payload.set_payload(attachment.read())
    payload.add_header("Content-Disposition", "attachment; filename= %s" % filename)
    msg.attach(payload)
    return msg


def _read_file(file_path):
    _file = open(file_path, "rb")
    return _file.read()


def build_mail_message_dto(sender, receiver, file_path):
    _subject = "ILBDOTI_test_CHIEF_licenceUpdate_1010_201901130300"
    return EmailMessageDto(
        run_number=1010,
        sender=sender,
        receiver=receiver,
        body="mail body",
        subject=_subject,
        attachment=[_subject, _read_file(file_path)],
        raw_data=build_text_message(sender, receiver, "mail body ..."),
    )

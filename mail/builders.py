from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_text_message(sender, receiver):
    """build a message of `MineMultipart` with a text attachment and octet-stream payload.\n
        Todo: using a custom builder to build mail message
    """
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = "Subject of the Mail run number: 99"
    body = "Body_of_the_mail 2"
    msg.attach(MIMEText(body, "plain"))
    filename = "File_name_with_extension"
    attachment = open("/path/to/afile", "rb")
    payload = MIMEBase("application", "octet-stream")
    payload.set_payload(attachment.read())
    payload.add_header("Content-Disposition", "attachment; filename= %s" % filename)
    msg.attach(payload)
    return msg

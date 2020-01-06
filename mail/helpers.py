from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_and_send_message(server, sender, receiver):
    message = _build_message(sender, receiver)
    server.send_email(
        "charles@example.com", "test18@example.com", message,
    )


# Let's do an assessment of using MIME rather than a custom
# builder and find out whether we should be using
# octet-stream as our encoding standard.
def _build_message(sender, receiver):
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = "Subject of the Mail run number: 99"
    body = "Body_of_the_mail"
    msg.attach(MIMEText(body, "plain"))
    filename = "File_name_with_extension"
    attachment = open("/path/to/file", "rb")
    payload = MIMEBase("application", "octet-stream")
    payload.set_payload((attachment).read())
    payload.add_header("Content-Disposition", "attachment; filename= %s" % filename)
    msg.attach(payload)
    return msg.as_string()

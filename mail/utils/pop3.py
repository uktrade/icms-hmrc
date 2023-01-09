import contextlib
import email
import poplib
from typing import List

from mail.auth import Authenticator
from mail.servers import MailServer

# TODO: CHECK correct encoding before going live
#   lite-hmrc used this setting for its pop code: DEFAULT_ENCODING = "iso-8859-1"


@contextlib.contextmanager
def get_connection(auth: Authenticator, hostname: str, port: int) -> poplib.POP3:
    ms = MailServer(auth, hostname=hostname, pop3_port=port)

    try:
        yield ms.connect_to_pop3()

    finally:
        ms.quit_pop3_connection()


def list_messages_ids(con: poplib.POP3) -> List[str]:
    resp, messages, octets = con.list()

    # m = 'mesg_num octets'
    return [m.decode().split(" ")[0] for m in messages]


def retrieve_message(con: poplib.POP3, msg_id: str) -> str:
    resp: bytes  # e.g. b'+OK'
    msg_lines: List[bytes]
    octets: int  # e.g. 8921

    resp, msg_lines, octets = con.retr(msg_id)

    return "\n".join(line.decode() for line in msg_lines)


def get_email(con: poplib.POP3, msg_id: str) -> email.message.EmailMessage:
    msg = retrieve_message(con, msg_id)

    message = email.message_from_string(msg, policy=email.policy.default)

    return message

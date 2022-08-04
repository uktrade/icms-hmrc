import logging
import poplib
import smtplib

from django.conf import settings

from mail.auth import Authenticator


class MailServer(object):
    def __init__(
        self,
        auth: Authenticator,
        hostname: str = settings.EMAIL_HOSTNAME,
        pop3_port: int = settings.EMAIL_POP3_PORT,
    ):
        self.auth = auth
        self.pop3_port = pop3_port
        self.hostname = hostname
        self.pop3_connection = None

    def __eq__(self, other):

        if not isinstance(other, MailServer):
            return False

        return self.hostname == other.hostname and self.auth == other.auth and self.pop3_port == other.pop3_port

    def connect_to_pop3(self) -> poplib.POP3_SSL:
        logging.info("establishing a pop3 connection...")
        self.pop3_connection = poplib.POP3_SSL(self.hostname, self.pop3_port, timeout=60)
        self.auth.authenticate(self.pop3_connection)
        logging.info("pop3 connection established")
        return self.pop3_connection

    def quit_pop3_connection(self):
        self.pop3_connection.quit()


def get_smtp_connection():
    """Connect to an SMTP server, specified by environment variables."""
    # Note that EMAIL_HOSTNAME is not Django's EMAIL_HOST setting.
    hostname = settings.EMAIL_HOSTNAME
    port = str(settings.EMAIL_SMTP_PORT)
    use_tls = settings.EMAIL_USE_TLS
    username = settings.EMAIL_USER
    password = settings.EMAIL_PASSWORD
    logging.info("SMTP=%r:%r, TLS=%r, USERNAME=%r", hostname, port, use_tls, username)
    conn = smtplib.SMTP(hostname, port, timeout=60)

    if use_tls:
        conn.starttls()

    conn.login(username, password)

    return conn


def smtp_send(message):
    conn = get_smtp_connection()
    try:
        # Result is an empty dict on success.
        result = conn.send_message(message)
    finally:
        conn.quit()

    return result

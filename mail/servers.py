import logging
import poplib
import smtplib

from django.conf import settings


class MailServer(object):
    def __init__(
        self,
        hostname: str = settings.EMAIL_HOSTNAME,
        user: str = settings.EMAIL_USER,
        password: str = settings.EMAIL_PASSWORD,
        pop3_port: int = settings.EMAIL_POP3_PORT,
        smtp_port: int = settings.EMAIL_SMTP_PORT,
        use_tls: bool = settings.EMAIL_USE_TLS,
    ):
        self.smtp_port = smtp_port
        self.pop3_port = pop3_port
        self.password = password
        self.user = user
        self.hostname = hostname
        self.pop3_connection = None
        self.smtp_connection = None
        self.use_tls = use_tls

    def __eq__(self, other):

        if not isinstance(other, MailServer):
            return False

        # noinspection TimingAttack
        return (
            self.hostname == other.hostname
            and self.user == other.user
            and self.password == other.password
            and self.pop3_port == other.pop3_port
            and self.smtp_port == other.smtp_port
        )

    def connect_to_pop3(self) -> poplib.POP3_SSL:
        logging.info("establishing a pop3 connection...")
        self.pop3_connection = poplib.POP3_SSL(self.hostname, self.pop3_port, timeout=60)
        self.pop3_connection.user(self.user)
        self.pop3_connection.pass_(self.password)
        logging.info("pop3 connection established")
        return self.pop3_connection

    def quit_pop3_connection(self):
        self.pop3_connection.quit()

    def connect_to_smtp(self) -> smtplib.SMTP:
        logging.info("establishing an smtp connection...")
        self.smtp_connection = smtplib.SMTP(self.hostname, str(self.smtp_port), timeout=60)
        logging.info("smtp connection established")
        if self.use_tls:
            logging.info("starting tls...")
            self.smtp_connection.starttls()
            logging.info("tls started")
        logging.info("logging in...")
        self.smtp_connection.login(self.user, self.password)
        logging.info("logged in")
        return self.smtp_connection

    def quit_smtp_connection(self):
        self.smtp_connection.quit()

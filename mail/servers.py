import logging
import poplib
import typing

from django.conf import settings
from django.core import mail

from mail import enums


def get_smtp_connection(name: typing.Optional[enums.SMTPConnection] = None):
    """Return the Django mail backend configured for use."""
    # By using Django's mail stuff, we get the Django mail testing stuff too.
    configs = {
        enums.SMTPConnection.INCOMING: "INCOMING_",
        enums.SMTPConnection.HMRC: "HMRC_TO_DIT_",
        enums.SMTPConnection.MOCK: "MOCK_HMRC_",
        enums.SMTPConnection.SPIRE: "SPIRE_STANDIN_",
    }

    if name in configs:
        # Map to the custom settings names, e.g. HMRC_TO_DIT_EMAIL_HOSTNAME.
        prefix = configs[name]
        kwargs = {
            "EMAIL_HOST": getattr(settings, prefix + "EMAIL_HOSTNAME"),
            "EMAIL_HOST_USER": getattr(settings, prefix + "EMAIL_USER"),
            "EMAIL_HOST_PASSWORD": getattr(settings, prefix + "EMAIL_PASSWORD"),
            "EMAIL_USE_TLS": True,
            "EMAIL_PORT": getattr(settings, prefix + "EMAIL_SMTP_PORT"),
        }
    else:
        # Use Django's default config settings names.
        kwargs = {}

    return mail.get_connection(**kwargs)


class MailServer(object):
    def __init__(
        self,
        hostname: str = settings.EMAIL_HOSTNAME,
        user: str = settings.EMAIL_USER,
        password: str = settings.EMAIL_PASSWORD,
        pop3_port: int = settings.EMAIL_POP3_PORT,
        use_tls: bool = settings.EMAIL_USE_TLS,
    ):
        self.pop3_port = pop3_port
        self.password = password
        self.user = user
        self.hostname = hostname
        self.pop3_connection = None
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

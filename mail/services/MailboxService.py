import logging
from mail.services.helpers import to_mail_message_dto
from mail.services.logging_decorator import lite_log
from mail.models import Mail

logger = logging.getLogger(__name__)


class MailboxService(object):
    def __init__(self):
        pass

    def send_email(self, smtp_connection: object, message: object):
        smtp_connection.send_message(message)

    def read_last_message(self, pop3_connection: object):
        _, mails, _ = pop3_connection.list()
        return to_mail_message_dto(pop3_connection.retr(len(mails)))

    @staticmethod
    def find_mail_of(extract_type: str, reception_status: str):
        try:
            mail = Mail.objects.get(status=reception_status, extract_type=extract_type,)
            lite_log(
                logger,
                logging.DEBUG,
                "Found mail in {} of extract type {} ".format(
                    reception_status, extract_type
                ),
            )
            return mail
        except Mail.DoesNotExist as ex:
            lite_log(
                logger,
                logging.WARN,
                "Can not find any mail in [{}] of extract type [{}]".format(
                    reception_status, extract_type
                ),
            )
            raise ex

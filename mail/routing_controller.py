import logging

from mail.enums import ReceptionStatusEnum
from mail.servers import MailServer
from mail.services.MailboxService import MailboxService
from mail.services.data_processors import (
    serialize_email_message,
    to_email_message_dto_from,
    lock_db_for_sending_transaction,
)
from mail.services.helpers import build_email_message
from mail.services.logging_decorator import lite_logging_decorator


def check_and_route_emails():
    logging.info({"message": "liteolog hmrc", "status": "checking for emails"})
    last_message_dto = _read_last_message()
    mail = serialize_email_message(last_message_dto)
    if not mail:
        logging.info(
            {"message": "liteolog hmrc", "info": "last email considered invalid"}
        )
        return 1
    return _collect_and_send(mail)


def _update_mail_status(mail):
    if mail.status == ReceptionStatusEnum.PENDING:
        mail.status = ReceptionStatusEnum.REPLY_PENDING
    else:
        mail.status = ReceptionStatusEnum.REPLY_SENT
    mail.save()


def _collect_and_send(mail):
    logging.info({"message": "liteolog hmrc", "info": "mail id being sent"})
    message_to_send_dto = to_email_message_dto_from(mail)
    is_locked_by_me = lock_db_for_sending_transaction(mail)
    if not is_locked_by_me:
        return "email being sent by another thread"
    _send(message_to_send_dto)
    _update_mail_status(mail)
    response_message = f"Email routed from {message_to_send_dto.sender} to {message_to_send_dto.receiver}"
    return response_message


@lite_logging_decorator
def _send(message_to_send_dto):
    server = MailServer()
    mail_box_service = MailboxService()
    smtp_connection = server.connect_to_smtp()
    mail_box_service.send_email(
        smtp_connection, build_email_message(message_to_send_dto)
    )
    server.quit_smtp_connection()


def _read_last_message():
    server = MailServer()
    mail_box_service = MailboxService()
    pop3_connection = server.connect_to_pop3()
    last_msg_dto = mail_box_service.read_last_message(pop3_connection)
    server.quit_pop3_connection()
    return last_msg_dto

from datetime import datetime

from mail.servers import MailServer
from mail.services.MailboxService import MailboxService
from mail.services.data_processing import (
    process_and_save_email_message,
    to_email_message_dto_from,
    lock_db_for_sending_transaction,
)
from mail.services.helpers import build_email_message


def check_and_route_emails():
    print("checking mail at ", datetime.now(), "...")
    server = MailServer()
    mail_box_service = MailboxService()

    mail = read_and_save(server, mail_box_service)

    if not mail:
        print("Bad mail")
        return 1

    return collect_and_send(mail, server, mail_box_service)


def collect_and_send(mail, server, mail_box_service):
    message_to_send_dto = to_email_message_dto_from(mail)

    is_locked_by_me = lock_db_for_sending_transaction(mail)
    if not is_locked_by_me:
        return "email being sent by someone else"

    smtp_connection = server.connect_to_smtp()
    mail_box_service.send_email(
        smtp_connection, build_email_message(message_to_send_dto)
    )
    server.quit_smtp_connection()
    response_message = "Email routed from {} to {}".format("someone", "receiver tbd")
    return response_message


def read_and_save(server, mail_box_service):
    pop3_connection = server.connect_to_pop3()
    last_msg_dto = mail_box_service.read_last_message(pop3_connection)
    server.quit_pop3_connection()
    return process_and_save_email_message(last_msg_dto)

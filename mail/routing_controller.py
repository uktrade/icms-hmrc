from mail.servers import MailServer
from mail.services.MailboxService import MailboxService
from mail.services.data_processing import (
    process_and_save_email_message,
    collect_and_send_data_to_dto,
)
from mail.services.helpers import build_msg


def check_and_route_emails():
    server = MailServer()
    mail_box_service = MailboxService()
    pop3_connection = server.connect_to_pop3()
    last_msg_dto = mail_box_service.read_last_message(pop3_connection)
    server.quit_pop3_connection()
    mail = process_and_save_email_message(last_msg_dto)
    if not mail:
        raise Exception
    message_to_send_dto = collect_and_send_data_to_dto(mail)
    smtp_connection = server.connect_to_smtp()
    mail_box_service.send_email(smtp_connection, build_msg(message_to_send_dto))
    server.quit_smtp_connection()

    response_message = "Email routed from {} to {}".format(
        last_msg_dto.sender, "receiver tbd"
    )
    return response_message

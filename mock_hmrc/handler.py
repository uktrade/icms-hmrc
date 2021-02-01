import logging

from mail.libraries.helpers import to_hmrc_mail_message_dto
from mail.libraries.routing_controller import get_mock_hmrc_mailserver
from mail.libraries.mailbox_service import get_message_id
from mock_hmrc import models
from mock_hmrc.data_processors import save_hmrc_email_message_data


def get_hmrc_email_message_dto(server):
    conn = server.connect_to_pop3()
    _, mails, _ = conn.list()
    message_ids = [get_message_id(line.decode("utf-8")) for line in mails]

    if models.RetrievedMail.objects.count():
        recent_mail = models.RetrievedMail.objects.all().order_by("message_id").last()
        target_id = None
        for msg_id in message_ids:
            if msg_id > recent_mail.message_id:
                target_id = msg_id
                break
    else:
        target_id = message_ids[0]

    dto = None
    if target_id:
        email = conn.retr(target_id)
        dto = to_hmrc_mail_message_dto(target_id, email)

    server.quit_pop3_connection()

    return dto


def parse_and_reply_emails():
    server = get_mock_hmrc_mailserver()
    email_dto = get_hmrc_email_message_dto(server)
    if not email_dto:
        logging.info("No emails to process or invalid")
        return

    save_hmrc_email_message_data(email_dto)

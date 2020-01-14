import logging

from mail.servers import MailServer
from mail.services.MailboxService import MailboxService

log = logging.getLogger(__name__)


def read_email_job():
    server = MailServer()
    pop3_conn = server.connect_to_pop3()
    log.info("Last message: \n%s.", str(MailboxService().read_last_message(pop3_conn)))
    server.quit_pop3_connection()
    # TODO: Some logic which does the following:
    #   - reads the 'last_message'
    #   - Saves the message in a table (against a sent message if it is a reply)
    #   - Reads the sender
    #   - Records run number and if required and adjusts run number
    #   - calls build_and_send_message with new receiver address (keep the sender)
    #   - records the send message in table

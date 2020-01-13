from conf.settings import EMAIL_PASSWORD
from mail.servers import MailServer
from mail.services.MailboxService import MailboxService
import logging

log = logging.getLogger(__name__)


def reademail_job():
    server = MailServer(
        hostname="localhost",
        user="test18",
        pwd=EMAIL_PASSWORD,
        pop3_port=995,
        smtp_port=587,
    )
    pop3_conn = server.connect_pop3()
    log.info("Last message: \n%s.", str(MailboxService().read_last_message(pop3_conn)))
    pop3_conn.quit()
    # TODO: Some logic which does the following:
    #   - reads the 'last_message'
    #   - Saves the message in a table (against a sent message if it is a reply)
    #   - Reads the sender
    #   - Records run number and if required and adjusts run number
    #   - calls build_and_send_message with new receiver address (keep the sender)
    #   - records the send message in table

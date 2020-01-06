from mail.servers import MailServer


def reademail_job():
    server = MailServer()
    mail_msg = server.read_email()

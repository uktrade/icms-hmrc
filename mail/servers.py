import poplib
import smtplib


class MailServer(object):
    def __init__(self, hostname, user, pwd, pop3_port: int, smtp_port: int):
        self.smtp_port = smtp_port
        self.pop3_port = pop3_port
        self.pwd = pwd
        self.user = user
        self.hostname = hostname

    def connect_pop3(self):
        pop3 = poplib.POP3_SSL(self.hostname, str(self.pop3_port))
        pop3.user(self.user)
        pop3.pass_(self.pwd)
        return pop3

    def connect_smtp(self):
        smtp = smtplib.SMTP(self.hostname, str(self.smtp_port))
        smtp.starttls()
        smtp.login(self.user, self.pwd)
        return smtp

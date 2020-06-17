import json
import uuid
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from django.db import models
from django.utils import timezone
from jsonfield import JSONField

from conf.settings import EMAIL_USER, NOTIFY_USERS
from mail.enums import ReceptionStatusEnum, ExtractTypeEnum, SourceEnum, LicenceActionEnum, ReplyStatusEnum
from mail.servers import MailServer


class Mail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    edi_filename = models.TextField(null=True, blank=True)
    edi_data = models.TextField(null=True, blank=True)
    status = models.CharField(choices=ReceptionStatusEnum.choices, default=ReceptionStatusEnum.PENDING, max_length=20)
    extract_type = models.CharField(choices=ExtractTypeEnum.choices, max_length=20, null=True)

    sent_filename = models.TextField(blank=True, null=True)
    sent_data = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    response_filename = models.TextField(blank=True, null=True)
    response_data = models.TextField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)
    response_subject = models.TextField(null=True, blank=True)

    sent_response_filename = models.TextField(blank=True, null=True)
    sent_response_data = models.TextField(blank=True, null=True)

    raw_data = models.TextField()

    currently_processing_at = models.DateTimeField(null=True)
    currently_processed_by = models.CharField(null=True, max_length=100)

    class Meta:
        db_table = "mail"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        super(Mail, self).save(*args, **kwargs)

        if self.response_data and ReplyStatusEnum.REJECTED in self.response_data:
            self.send_rejection_notification_email(self.id, self.response_date)

    def set_locking_time(self, offset: int = 0):
        self.currently_processing_at = timezone.now() + timedelta(seconds=offset)
        self.save()

    def set_last_submitted_time(self, offset: int = 0):
        self.last_submitted_on = timezone.now() + timedelta(seconds=offset)
        self.save()

    def set_response_date_time(self, offset: int = 0):
        self.response_date = timezone.now() + timedelta(seconds=offset)
        self.save()

    @staticmethod
    def send_rejection_notification_email(id, response_date):
        from mail.libraries.mailbox_service import send_email

        multipart_msg = MIMEMultipart()
        multipart_msg["From"] = EMAIL_USER
        multipart_msg["To"] = ",".join(NOTIFY_USERS)
        multipart_msg["Subject"] = f"Mail rejected"
        body = MIMEText(f"Mail [{id}] received at [{response_date}] was rejected")
        multipart_msg.attach(body)

        server = MailServer()
        smtp_connection = server.connect_to_smtp()
        send_email(smtp_connection, multipart_msg)
        server.quit_smtp_connection()


class LicenceUpdate(models.Model):
    licence_ids = models.TextField()
    hmrc_run_number = models.IntegerField()
    source_run_number = models.IntegerField(null=True)
    source = models.CharField(choices=SourceEnum.choices, max_length=10)
    mail = models.ForeignKey(Mail, on_delete=models.DO_NOTHING)

    def set_licence_ids(self, data: List):
        self.licence_ids = json.dumps(data)

    def get_licence_ids(self):
        return json.loads(self.licence_ids)


class UsageUpdate(models.Model):
    licence_ids = models.TextField()
    mail = models.ForeignKey(Mail, on_delete=models.DO_NOTHING)
    spire_run_number = models.IntegerField()
    hmrc_run_number = models.IntegerField()

    def set_licence_ids(self, data: List):
        self.licence_ids = json.dumps(data)

    def get_licence_ids(self):
        return json.loads(self.licence_ids)


class LicencePayload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Convenience field for cross-referencing LITE services
    lite_id = models.CharField(null=False, blank=False, max_length=36)
    reference = models.CharField(null=False, blank=False, max_length=35)
    action = models.CharField(choices=LicenceActionEnum.choices, null=False, blank=False, max_length=6)
    data = JSONField()
    received_at = models.DateTimeField(default=timezone.now)
    is_processed = models.BooleanField(default=False)


class OrganisationIdMapping(models.Model):
    lite_id = models.CharField(unique=True, null=False, blank=False, max_length=36)
    rpa_trader_id = models.AutoField(primary_key=True)


class GoodIdMapping(models.Model):
    lite_id = models.CharField(null=False, blank=False, max_length=36)
    licence_reference = models.CharField(null=False, blank=False, max_length=35)
    line_number = models.PositiveIntegerField()

    class Meta:
        unique_together = [["lite_id", "licence_reference"]]

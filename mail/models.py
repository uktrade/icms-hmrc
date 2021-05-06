import json
import uuid
from datetime import timedelta
from typing import List

from django.db import models
from django.utils import timezone
from jsonfield import JSONField
from model_utils.models import TimeStampedModel

from mail.enums import (
    ReceptionStatusEnum,
    ExtractTypeEnum,
    SourceEnum,
    LicenceActionEnum,
    ReplyStatusEnum,
    MailReadStatuses,
)


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

    retry = models.BooleanField(default=False)

    class Meta:
        db_table = "mail"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        super(Mail, self).save(*args, **kwargs)

        if self.response_data and ReplyStatusEnum.REJECTED in self.response_data:
            self.notify_users(self.id, self.response_date)

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
    def notify_users(id, response_date):
        from mail.tasks import notify_users_of_rejected_mail

        notify_users_of_rejected_mail(str(id), str(response_date))


class LicenceData(models.Model):
    licence_ids = models.TextField()
    hmrc_run_number = models.IntegerField()
    source_run_number = models.IntegerField(null=True)
    source = models.CharField(choices=SourceEnum.choices, max_length=10)
    mail = models.ForeignKey(Mail, on_delete=models.DO_NOTHING)

    class Meta:
        ordering = ["mail__created_at"]

    def set_licence_ids(self, data: List):
        self.licence_ids = json.dumps(data)

    def get_licence_ids(self):
        return json.loads(self.licence_ids)


class UsageData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    licence_ids = JSONField()
    mail = models.ForeignKey(Mail, on_delete=models.DO_NOTHING, null=False)
    spire_run_number = models.IntegerField()
    hmrc_run_number = models.IntegerField()
    has_lite_data = models.NullBooleanField(default=None)
    has_spire_data = models.NullBooleanField(default=None)
    lite_payload = JSONField()
    lite_sent_at = models.DateTimeField(blank=True, null=True)  # When update was sent to LITE API
    lite_accepted_licences = JSONField()
    lite_rejected_licences = JSONField()
    spire_accepted_licences = JSONField()
    spire_rejected_licences = JSONField()
    lite_licences = JSONField()
    spire_licences = JSONField()
    lite_response = JSONField()

    class Meta:
        ordering = ["mail__created_at"]

    def get_licence_ids(self):
        return json.loads(self.licence_ids)

    @staticmethod
    def send_usage_updates_to_lite(id):
        from mail.tasks import schedule_licence_usage_figures_for_lite_api

        schedule_licence_usage_figures_for_lite_api(str(id))


class LicencePayload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lite_id = models.UUIDField(null=False, blank=False, unique=False)
    reference = models.CharField(null=False, blank=False, max_length=35)
    action = models.CharField(choices=LicenceActionEnum.choices, null=False, blank=False, max_length=6)
    data = JSONField()
    received_at = models.DateTimeField(default=timezone.now)
    is_processed = models.BooleanField(default=False)

    # For updates only
    old_lite_id = models.UUIDField(null=True, blank=False, unique=False)
    old_reference = models.CharField(null=True, blank=False, max_length=35)

    class Meta:
        unique_together = [["lite_id", "action"]]
        ordering = ["received_at"]

    def save(self, *args, **kwargs):
        super(LicencePayload, self).save(*args, **kwargs)
        LicenceIdMapping.objects.get_or_create(lite_id=self.lite_id, reference=self.reference)


class LicenceIdMapping(models.Model):
    lite_id = models.UUIDField(primary_key=True, null=False, blank=False)
    reference = models.CharField(null=False, blank=False, max_length=35, unique=True)


class OrganisationIdMapping(models.Model):
    lite_id = models.UUIDField(null=False, blank=False)
    rpa_trader_id = models.AutoField(primary_key=True)


class GoodIdMapping(models.Model):
    lite_id = models.UUIDField(primary_key=False, null=False, blank=False, unique=False)
    licence_reference = models.CharField(null=False, blank=False, max_length=35, unique=False)
    line_number = models.PositiveIntegerField()

    class Meta:
        unique_together = [["lite_id", "licence_reference"]]


class TransactionMapping(models.Model):
    licence_reference = models.CharField(null=False, blank=False, max_length=35, unique=False)
    line_number = models.PositiveIntegerField(null=True, blank=True)
    usage_transaction = models.CharField(null=False, blank=False, max_length=35)
    usage_data = models.ForeignKey(UsageData, on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = [["licence_reference", "line_number", "usage_data"]]


class MailboxConfig(TimeStampedModel):
    username = models.TextField(null=False, blank=False, primary_key=True, help_text="Username of the POP3 mailbox")
    start_message_id = models.TextField(
        null=True,
        blank=False,
        default=None,
        help_text="Process messages from this message ID onwards, can be Null if messages should be processed from the very first message in the mailbox",
    )


class MailReadStatus(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_id = models.TextField()
    status = models.TextField(choices=MailReadStatuses.choices, default=MailReadStatuses.UNREAD, db_index=True)
    mailbox = models.ForeignKey(MailboxConfig, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.__class__.__name__}(message_id={self.message_id}, status={self.status})"

import json
import uuid
from typing import List

from django.db import models
from django.db.models import Q

from mail.enums import ReceptionStatusEnum, ExtractTypeEnum, SourceEnum


class MailManager(models.Manager):
    def invalid(self):
        return self.filter(Q(errors__isnull=False) | Q(serializer_errors__isnull=False))

    def valid(self):
        return self.filter(Q(errors__isnull=True) & Q(serializer_errors__isnull=True))


class Mail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    last_submitted_on = models.DateTimeField(
        blank=True, null=True
    )  # TODO: Investigate what this is
    edi_filename = models.TextField(null=True, blank=True)
    edi_data = models.TextField(null=True, blank=True)
    status = models.CharField(
        choices=ReceptionStatusEnum.choices, null=True, max_length=20
    )
    extract_type = models.CharField(
        choices=ExtractTypeEnum.choices, max_length=20, null=True
    )
    response_file = models.TextField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)

    raw_data = models.TextField()

    # To assist debugging invalid emails
    serializer_errors = models.TextField(blank=True, null=True)
    errors = models.TextField(blank=True, null=True)

    objects = MailManager()

    class Meta:
        ordering = ["created_at"]


class LicenceUpdate(models.Model):
    license_ids = models.TextField()
    hmrc_run_number = models.IntegerField()
    source_run_number = models.IntegerField(null=True)
    source = models.CharField(choices=SourceEnum.choices, max_length=10)
    mail = models.ForeignKey(Mail, on_delete=models.DO_NOTHING)

    def set_licence_ids(self, data: List):
        self.license_ids = json.dumps(data)

    def get_licence_ids(self):
        return json.loads(self.license_ids)


class LicenceUsage(models.Model):
    license_ids = models.TextField()
    mail = models.ForeignKey(Mail, on_delete=models.DO_NOTHING)

    def set_licence_ids(self, data: List):
        self.license_ids = json.dumps(data)

    def get_licence_ids(self):
        return json.loads(self.license_ids)

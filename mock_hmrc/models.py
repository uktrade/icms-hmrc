import uuid

from django.db import models

from mail.enums import ExtractTypeEnum
from mock_hmrc.enums import HmrcMailStatusEnum, RetrievedEmailStatusEnum


class RetrievedMail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_id = models.TextField()
    sender = models.TextField()
    status = models.TextField(choices=RetrievedEmailStatusEnum.choices, default=RetrievedEmailStatusEnum.INVALID)


class HmrcMail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    status = models.TextField(choices=HmrcMailStatusEnum.choices, default=HmrcMailStatusEnum.ACCEPTED)
    extract_type = models.TextField(choices=ExtractTypeEnum.choices, null=True)
    source = models.TextField()
    source_run_number = models.IntegerField()
    edi_filename = models.TextField()
    edi_data = models.TextField()
    licence_ids = models.TextField()

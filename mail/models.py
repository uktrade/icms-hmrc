import uuid

from django.db import models

from mail.enums import ReceptionStatusEnum, ExtractTypeEnum, SourceEnum


class Mail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    last_submitted_on = models.DateTimeField(
        blank=True, null=True
    )  # TODO: Investigate what this is
    edi_data = models.TextField()
    status = models.CharField(
        choices=ReceptionStatusEnum.choices, null=True, max_length=20
    )
    extract_type = models.CharField(choices=ExtractTypeEnum.choices, max_length=20)
    response_file = models.TextField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)
    edi_filename = models.TextField()
    raw_data = models.TextField()

    class Meta:
        ordering = ["created_at"]
        abstract = True


class LicenseUpdate(Mail):
    license_id = models.UUIDField()
    hmrc_run_number = models.IntegerField()
    source_run_number = models.IntegerField(null=True)
    source = models.CharField(choices=SourceEnum.choices, max_length=10)


class LicenseUsage(Mail):
    pass


class InvalidEmail(Mail):
    serializer_errors = models.TextField()
    extract_type = models.CharField(
        choices=ExtractTypeEnum.choices, max_length=20, null=True
    )
    edi_filename = models.TextField(null=True, blank=True)
    edi_data = models.TextField(null=True, blank=True)

import logging
import uuid

from django.db import IntegrityError, models
from django.utils import timezone

from mail.enums import ExtractTypeEnum, LicenceActionEnum, ReceptionStatusEnum, SourceEnum

logger = logging.getLogger(__name__)


class LicencePayload(models.Model):
    # TODO: Replace with BigAutoField primary keys (requires migrations to be squashed)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    lite_id = models.UUIDField(null=False, blank=False, unique=False)
    reference = models.CharField(null=False, blank=False, max_length=35)
    action = models.CharField(choices=LicenceActionEnum.choices, null=False, blank=False, max_length=7)
    data = models.JSONField(default=dict)
    received_at = models.DateTimeField(default=timezone.now)
    is_processed = models.BooleanField(default=False)

    # This allows us to skip License requests to be skipped
    skip_process = models.BooleanField(default=False)

    class Meta:
        unique_together = [["lite_id", "action"]]
        ordering = ["received_at"]

    def __str__(self):
        return f"LicencePayload(lite_id={self.lite_id}, reference={self.reference}, action={self.action})"


class LicenceData(models.Model):
    licence_ids = models.TextField()
    hmrc_run_number = models.IntegerField()
    source_run_number = models.IntegerField(null=True)
    source = models.CharField(choices=SourceEnum.choices, max_length=10)
    mail = models.ForeignKey("Mail", on_delete=models.DO_NOTHING)
    licence_payloads = models.ManyToManyField(
        "LicencePayload", help_text="LicencePayload records linked to this LicenceData instance", related_name="+"
    )

    class Meta:
        ordering = ["mail__created_at"]


class Mail(models.Model):
    # TODO: Replace with BigAutoField primary keys (requires migrations to be squashed)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # For licence_data / licence_reply emails they are saved on a single db record.
    # e.g. the licence_reply email is saved on the licence_data record
    extract_type = models.CharField(choices=ExtractTypeEnum.choices, max_length=20, null=True)

    # Status of mail through the lite-hmrc workflow
    status = models.CharField(choices=ReceptionStatusEnum.choices, default=ReceptionStatusEnum.PENDING, max_length=20)

    # licenceData fields
    edi_filename = models.TextField(null=True, blank=True)
    edi_data = models.TextField(null=True, blank=True)
    sent_filename = models.TextField(blank=True, null=True)
    sent_data = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    # licenceReply / Usage fields
    response_filename = models.TextField(blank=True, null=True)
    response_data = models.TextField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)
    response_subject = models.TextField(null=True, blank=True)

    sent_response_filename = models.TextField(blank=True, null=True)
    sent_response_data = models.TextField(blank=True, null=True)

    raw_data = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    currently_processing_at = models.DateTimeField(null=True)
    currently_processed_by = models.CharField(null=True, max_length=100)

    retry = models.BooleanField(default=False)

    class Meta:
        db_table = "mail"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.__class__.__name__} object (id={self.id}, status={self.status})"

    def save(self, *args, **kwargs):
        if not self.edi_data or not self.edi_filename:
            logger.error(
                "Setting `edi_data` or `edi_filename` to null or blank: self=%s, edi_data=%s edi_filename=%s",
                self,
                self.edi_data,
                self.edi_filename,
                exc_info=True,
            )
            raise IntegrityError("The field edi_filename or edi_data is empty which is not valid")

        super(Mail, self).save(*args, **kwargs)

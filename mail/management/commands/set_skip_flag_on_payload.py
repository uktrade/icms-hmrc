import logging

from django.core.management.base import BaseCommand

from mail.models import LicencePayload

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Command to set the skip flag on a LicensePayload object. By setting to true the License object is skipped and halts
    processing. The license request won't be sent to HMRC until we set the flag to false again. This is designed to
    prevent single bad payload objects from blocking the queue.

    Arguments:
    reference: Use to identify a license payload object.
    skip_process: Set to true to stop process of payload object
    dry_run: Check if license payload object exists no DB changes take place

    -------------------------
    When to use this command
    -------------------------
    Use this command when we have a payload object that is breaking the queue for example during a validation error
    set skip flag to true to skip processing
    """

    def add_arguments(self, parser):
        parser.add_argument("--reference", type=str, nargs="?", help="License reference number of the license payload")
        parser.add_argument(
            "--skip_process", type=str, nargs="?", help="To skip processing set to true", default="False"
        )
        parser.add_argument("--dry_run", help="Is it a test run?", action="store_true")

    def handle(self, *args, **options):
        dry_run = options.pop("dry_run")
        reference = options.pop("reference")
        skip_process = options.pop("skip_process")

        payload = LicencePayload.objects.get(reference=reference)
        payload.skip_process = skip_process

        if payload.is_processed:
            logger.info("The payload object has already been processed unable to set skip flag")
        elif not dry_run:
            payload.save()
            logger.info("Reference %s skip_process set to %s", reference, payload.skip_process)
        else:
            logger.info("DRY RUN : Reference %s skip_process set to %s", reference, payload.skip_process)

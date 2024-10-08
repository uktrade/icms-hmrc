import email
import logging
import time
from email.headerregistry import Address, UniqueAddressHeader
from typing import Any, Dict
from urllib import parse

import requests
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from sentry_sdk import capture_message

from conf import celery_app
from mail import requests as mail_requests
from mail import utils
from mail.auth import Authenticator, ModernAuthentication
from mail.chief.email import build_request_mail_message_dto
from mail.chief.licence_data import create_licence_data_mail
from mail.chief.licence_reply import LicenceReplyProcessor
from mail.chief.usage_data.processor import UsageDataProcessor
from mail.email.utils import send_email_wrapper
from mail.enums import ExtractTypeEnum, MailStatusEnum, SourceEnum
from mail.models import LicenceData, LicencePayload, Mail
from mail.utils import pop3
from mail.utils.sentry import log_to_sentry

logger = logging.getLogger(__name__)


@celery_app.task(name="icms:dev_process_hmrc_licence_data")
def dev_process_hmrc_licence_data() -> None:
    """Run all tasks in one task for speed when in a development environment."""

    if utils.is_production_environment():
        logger.warning("This command is only for development environments")
        return

    steps = [
        ("Sending licence data to HMRC", send_licence_data_to_hmrc),
        ("Faking LicenceReply email from HMRC CHIEF", fake_licence_reply),
        ("Sending licence data to ICMS", send_licence_data_to_icms),
        ("Sending usage data to ICMS", send_usage_data_to_icms),
    ]

    for i, (msg, step) in enumerate(steps, start=1):
        logger.info(f">>>> STEP {i}: {msg}")
        step.apply()

        time.sleep(5)


@celery_app.task(name="icms:send_licence_data_to_hmrc")
def send_licence_data_to_hmrc() -> None:
    """Sends ICMS licence updates to HMRC."""

    source = SourceEnum.ICMS
    logger.info("Sending %s licence updates to HMRC", source)

    if (
        Mail.objects.filter(extract_type=ExtractTypeEnum.LICENCE_DATA)
        # Data already sent back to ICMS
        .exclude(status=MailStatusEnum.REPLY_PROCESSED).count()
    ):
        # One of the following is happening:
        # 1. We are in the process of creating a mail record for sending (PENDING)
        # 2. We have already sent a record to HMRC (REPLY_PENDING)
        # 3. We have received a reply from HMRC and are going to process it (REPLY_RECEIVED)
        # 4. We have an error we need to resolve (REPLY_PARTIALLY_PROCESSED)
        logger.info("Unable to send licence data to HMRC as we are processing another mail record.")

        return

    try:
        with transaction.atomic():
            licences = LicencePayload.objects.filter(is_processed=False).select_for_update()

            if not licences.exists():
                logger.info("There are currently no licences to send")
                return

            mail = create_licence_data_mail(licences, source)
            mail_dto = build_request_mail_message_dto(mail)
            licence_references = [licence.reference for licence in licences]
            logger.info(
                "Created Mail [%s] with subject %s from licences [%s]",
                mail.id,
                mail_dto.subject,
                licence_references,
            )

            send_email_wrapper(mail_dto)

            # Update the mail object to indicate we are waiting for a reply from HMRC.
            mail.status = MailStatusEnum.REPLY_PENDING
            mail.sent_at = timezone.now()
            mail.save()

            licences.update(is_processed=True)
            logger.info("Licence references [%s] marked as processed", licence_references)

            logger.info(
                "Successfully sent %s licences updates in Mail [%s] to HMRC", source, mail.id
            )

    except ValueError as err:  # noqa
        raise err
    except Exception as exc:  # noqa
        logger.error(
            "An unexpected error occurred when sending %s licence updates to HMRC -> %s",
            source,
            type(exc).__name__,
            exc_info=True,
        )


@celery_app.task(name="icms:fake_licence_reply")
def fake_licence_reply():
    if utils.is_production_environment():
        logger.warning("This command is only for development environments")
        return

    call_command("dev_fake_licence_reply", settings.ICMS_FAKE_HMRC_REPLY)


@celery_app.task(name="icms:process_licence_reply_and_usage_emails")
def process_licence_reply_and_usage_emails():
    """Downloads licenceReply and usageData emails from HMRC mailbox and stores in Mail model."""

    logger.info("Checking for reply and usage emails")

    auth = get_licence_reply_mailbox_auth()
    mailbox_hostname = settings.INCOMING_EMAIL_HOSTNAME
    port = settings.INCOMING_EMAIL_POP3_PORT

    with transaction.atomic(), pop3.get_connection(auth, mailbox_hostname, port) as con:
        try:
            for msg_id in pop3.list_messages_ids(con):
                logger.debug("Processing msg_id %s", msg_id)

                mail = pop3.get_email(con, msg_id)

                check_sender_valid(
                    mail,
                    expected_sender_domain=settings.HMRC_TO_DIT_EMAIL_HOSTNAME,
                    expected_sender_user=settings.HMRC_TO_DIT_EMAIL_USER,
                )

                subject = mail.get("Subject")
                logger.debug("Subject of email being processed: %s", subject)

                if "licenceReply" in subject:
                    _save_licence_reply_email(mail)
                    con.dele(msg_id)

                elif "usageData" in subject:
                    _save_usage_data_email(mail)
                    con.dele(msg_id)
                else:
                    # LicenceData files get sent via a different mailbox so the below sentry
                    # should never happen (for licenceData files).
                    # e.g. licenceData files get sent here will produce error logs.
                    log_to_sentry(f"Unable to process email with subject: {subject}")

        except Exception as e:
            con.rset()
            raise e


@celery_app.task(name="icms:send_licence_data_to_icms")
@transaction.atomic()
def send_licence_data_to_icms():
    """Checks Mail model for any licence reply records to send to ICMS."""

    logger.info("Checking for licence data to send to ICMS")

    licence_reply_mail_qs = Mail.objects.filter(
        extract_type=ExtractTypeEnum.LICENCE_DATA, status=MailStatusEnum.REPLY_RECEIVED
    )

    mail_to_process = licence_reply_mail_qs.count()

    if mail_to_process == 0:
        logger.info("No licence date found to send to ICMS")
        return

    if mail_to_process > 1:
        raise ValueError("Unable to process mail as there are more than 1 records.")

    mail = licence_reply_mail_qs.select_for_update().first()

    processor = LicenceReplyProcessor.load_from_mail(mail)

    if processor.reply_file_is_valid():
        licence_reply_data = _get_licence_reply_data(processor)

        url = parse.urljoin(settings.ICMS_API_URL, "chief/license-data-callback")
        response: requests.Response = mail_requests.post(
            url,
            licence_reply_data,
            hawk_credentials=settings.ICMS_API_ID,
            timeout=settings.ICMS_API_REQUEST_TIMEOUT,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.error(
                "Failed to send licence reply data to ICMS (Check ICMS sentry): %s", str(e)
            )

            return

        # Update the status if everything was successful
        mail.status = MailStatusEnum.REPLY_PROCESSED
        mail.save()
        logger.info(
            "Successfully sent mail (id: %s, filename: %s) to ICMS for processing",
            mail.id,
            mail.response_filename,
        )
    elif processor.reply_file_is_invalid():
        error_msg = f"Unable to process mail (id: {mail.id}, filename: {mail.response_filename}) as it has file errors."
        logger.warning(error_msg)

        for file_error in processor.file_errors:
            logger.warning(
                "File error: position: %s, code: %s, error_msg: %s",
                file_error.position,
                file_error.code,
                file_error.text,
            )

        if not processor.file_trailer_valid():
            logger.warning(
                "File trailer count is different from processor count of accepted and rejected"
            )

        raise ValueError(error_msg)

    elif processor.reply_file_is_partially_valid():
        licence_reply_data = _get_licence_reply_data(processor)

        url = parse.urljoin(settings.ICMS_API_URL, "chief/license-data-callback")
        response: requests.Response = mail_requests.post(
            url,
            licence_reply_data,
            hawk_credentials=settings.ICMS_API_ID,
            timeout=settings.ICMS_API_REQUEST_TIMEOUT,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.error(
                "Failed to send licence reply data to ICMS (Check ICMS sentry): %s", str(e)
            )

            return

        # Update the status indicating we have partially processed some of the records
        mail.status = MailStatusEnum.REPLY_PARTIALLY_PROCESSED
        mail.save()

        # Send warning to sentry indicating we need to fix the records not processed by CHIEF
        # See mail/management/commands/recreate_and_send_licence_data_email.py
        capture_message(
            f"Successfully sent mail (id: {mail.id}, filename: {mail.response_filename}) to ICMS for processing but not all records were processed.",
            level="error",
        )

    # This should never happen...
    elif processor.reply_file_contains_no_data():
        capture_message(
            f"Check the following mail record: {mail.id}, manually set mail.status to REPLY_PROCESSED if there is no data in the reply file.",
            level="error",
        )

    # This should never happen...
    else:
        capture_message(f"Licence data in Mail: {mail} is in an unknown state.")


def _get_licence_reply_data(processor: LicenceReplyProcessor) -> Dict[str, Any]:
    # Load all LicencePayload records linked to the current LicenceData record
    ld: LicenceData = LicenceData.objects.get(hmrc_run_number=processor.file_header.run_num)
    current_licences = ld.licence_payloads.all().values_list("icms_id", "reference", named=True)

    # Create a mapping of transaction reference to the UUID ICMS sent originally
    id_map = {lp.reference: str(lp.icms_id) for lp in current_licences}

    licence_reply_data = {
        "run_number": processor.file_header.run_num,
        "accepted": [{"id": id_map[at.transaction_ref]} for at in processor.accepted_licences],
        "rejected": [
            {
                "id": id_map[rt.header.transaction_ref],
                "errors": [
                    {"error_code": error.code, "error_msg": error.text} for error in rt.errors
                ],
            }
            for rt in processor.rejected_licences
        ],
    }

    return licence_reply_data


@celery_app.task(name="icms:send_usage_data_to_icms")
@transaction.atomic()
def send_usage_data_to_icms():
    """Checks Mail model for any usage data records to send to ICMS."""

    logger.info("Checking for usage data to send to ICMS")

    usage_data_mail_qs = Mail.objects.filter(
        extract_type=ExtractTypeEnum.USAGE_DATA, status=MailStatusEnum.REPLY_RECEIVED
    )

    mail_to_process = usage_data_mail_qs.count()

    if mail_to_process == 0:
        logger.info("No usage date found to send to ICMS")
        return

    if mail_to_process > 1:
        raise ValueError("Unable to process mail as there are more than 1 records.")

    mail = usage_data_mail_qs.select_for_update().first()

    processor = UsageDataProcessor.load_from_mail(mail)

    if not processor.file_valid():
        logger.warning(
            "UsageDataProcessor._usages count differs from file_trailer.transaction_count"
        )
        raise ValueError(
            f"Unable to process mail (id: {mail.id}, filename: {mail.response_filename}) as it has file errors."
        )

    if len(processor.usage_licences) == 0:
        logger.info("No usage records to send to ICMS")
    else:
        logger.info("Sending usage records to ICMS")
        url = parse.urljoin(settings.ICMS_API_URL, "chief/usage-data-callback")
        response: requests.Response = mail_requests.post(
            url,
            {"usage_data": processor.usage_licences},
            hawk_credentials=settings.ICMS_API_ID,
            timeout=settings.ICMS_API_REQUEST_TIMEOUT,
        )

        try:
            response.raise_for_status()
            logger.info(
                "Successfully sent mail (id: %s, filename: %s) to ICMS for processing",
                mail.id,
                mail.response_filename,
            )
        except requests.HTTPError as e:
            logger.error("Failed to send usage data to ICMS (Check ICMS sentry): %s", str(e))

            return

    # Update the status if everything was successful
    mail.status = MailStatusEnum.REPLY_PROCESSED
    mail.save()


def get_licence_reply_mailbox_auth() -> Authenticator:
    """Mailbox that receives reply emails from HMRC.

    These are licenceReply and usageData emails.
    """

    return ModernAuthentication(
        user=settings.INCOMING_EMAIL_USER,
        client_id=settings.AZURE_AUTH_CLIENT_ID,
        client_secret=settings.AZURE_AUTH_CLIENT_SECRET,
        tenant_id=settings.AZURE_AUTH_TENANT_ID,
    )


def check_sender_valid(
    mail: email.message.EmailMessage, *, expected_sender_domain: str, expected_sender_user
) -> None:
    """Check the sender is valid"""

    mail_from_header: UniqueAddressHeader = mail.get("From")
    mail_from: Address = mail_from_header.addresses[0]

    if mail_from.domain != expected_sender_domain or mail_from.username != expected_sender_user:
        subject = mail.get("Subject")
        err_msg = f"Unable to verify incoming email: From:{mail_from}, Subject: {subject}"

        logger.warning(err_msg)

        raise ValueError(err_msg)


def _save_licence_reply_email(reply_email: email.message.EmailMessage) -> None:
    """Save the incoming licence reply email to the database."""

    subject = reply_email.get("Subject")
    run_number = _get_run_number_from_subject(subject)

    attachments = list(reply_email.iter_attachments())

    if not len(attachments) == 1:
        raise ValueError("Only one attachment is accepted per licence reply email.")

    reply_file = attachments[0]
    file_name = reply_file.get_filename()

    # e.g. b"1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\202203171606\\1\\N\r\n..."
    payload_bytes = reply_file.get_payload(decode=True)

    ld = LicenceData.objects.get(hmrc_run_number=run_number)

    mail = Mail.objects.select_for_update().get(id=ld.mail.id, status=MailStatusEnum.REPLY_PENDING)

    mail.status = MailStatusEnum.REPLY_RECEIVED
    mail.response_filename = file_name
    mail.response_data = payload_bytes.decode()
    mail.response_date = timezone.now()
    mail.response_subject = subject

    mail.save()

    logger.info(
        "Updated mail instance: %s with reply (subject: %s - filename: %s)",
        mail.id,
        subject,
        file_name,
    )


def _get_run_number_from_subject(s: str) -> int:
    try:
        if "licenceReply" in s:
            # e.g. CHIEF_licenceReply_29229_202209201442 -> 29229
            return int(s.split("_")[2])

        if "usageData" in s:
            # e.g. ILBDOTI_live_CHIEF_usageData_7132_202209280300 -> 7132
            return int(s.split("_")[4])

    except Exception as e:
        logger.error(e)

    raise ValueError(f"Unable to parse run number from {s!r}")


def _save_usage_data_email(usage_email: email.message.EmailMessage) -> None:
    subject = usage_email.get("Subject")

    logger.debug("usageData email subject: %s", subject)

    attachments = list(usage_email.iter_attachments())

    if not len(attachments) == 1:
        raise ValueError("Only one attachment is accepted per licence reply email.")

    reply_file = attachments[0]
    file_name = reply_file.get_filename()

    # e.g. b"1\\fileHeader\\CHIEF\\ILBDOTI\\usageData\\202209280300\\7132\\\r\n..."
    payload_bytes = reply_file.get_payload(decode=True)

    mail = Mail.objects.create(
        extract_type=ExtractTypeEnum.USAGE_DATA,
        status=MailStatusEnum.REPLY_RECEIVED,
        response_filename=file_name,
        response_data=payload_bytes.decode(),
        response_date=timezone.now(),
        response_subject=subject,
    )

    mail.response_data = payload_bytes.decode()
    mail.response_date = timezone.now()
    mail.response_subject = subject

    mail.save()

    logger.info(
        "Updated mail instance: %s with reply (subject: %s - filename: %s)",
        mail.id,
        subject,
        file_name,
    )

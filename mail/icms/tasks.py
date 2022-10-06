"""ICMS tasks that get periodically ran via django management commands."""

import email
import logging
from email.headerregistry import Address, UniqueAddressHeader

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from mail.auth import Authenticator, BasicAuthentication
from mail.enums import ReceptionStatusEnum
from mail.models import LicenceData, Mail
from mail.utils import pop3

logger = logging.getLogger(__name__)


def process_licence_reply_and_usage_emails():
    """Downloads licenceReply and usageData emails from HMRC mailbox and stores in Mail model."""

    logger.info("Checking for reply and usage emails")

    auth = _get_hmrc_mailbox_auth()
    mailbox_hostname = settings.INCOMING_EMAIL_HOSTNAME
    port = settings.INCOMING_EMAIL_POP3_PORT

    with transaction.atomic(), pop3.get_connection(auth, mailbox_hostname, port) as con:
        try:
            for msg_id in pop3.list_messages_ids(con):
                logger.debug("Processing msg_id %s", msg_id)

                mail = pop3.get_email(con, msg_id)

                _check_sender_valid(
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
                    raise ValueError(f"Unable to process email with subject: {subject}")

        except Exception as e:
            con.rset()
            raise e


# def send_licence_data_to_icms():
#     """Checks Mail model for any licence reply records to send to ICMS."""
#     raise NotImplementedError
#
#
# def send_usage_data_to_icms():
#     """Checks Mail model for any usage data records to send to ICMS."""
#     raise NotImplementedError


def _get_hmrc_mailbox_auth() -> Authenticator:
    # TODO: ICMSLST-1759 Replace with ModernAuthentication

    return BasicAuthentication(
        user=settings.INCOMING_EMAIL_USER,
        password=settings.INCOMING_EMAIL_PASSWORD,
    )


def _check_sender_valid(mail: email.message.EmailMessage, *, expected_sender_domain: str, expected_sender_user) -> None:
    """Check the sender is valid"""

    # TODO: ICMSLST-1760 Revisit this before going live.

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

    mail = Mail.objects.select_for_update().get(id=ld.mail.id, status=ReceptionStatusEnum.REPLY_PENDING)

    mail.status = ReceptionStatusEnum.REPLY_RECEIVED
    mail.response_filename = file_name
    mail.response_data = payload_bytes.decode()
    mail.response_date = timezone.now()
    mail.response_subject = subject

    mail.save()

    logger.info("Updated mail instance: %s with licence reply (subject: %s - filename: %s", mail.id, subject, file_name)


def _get_run_number_from_subject(s: str) -> int:
    try:
        if "licenceReply" in s:
            # e.g. CHIEF_licenceReply_29229_202209201442 -> 29229
            return int(s.split("_")[2])

        if "usageData" in s:
            # e.g. ILBDOTI_live_CHIEF_usageData_7132_202209280300
            return int(s.split("_")[4])

    except Exception as e:
        logger.error(e)

    raise ValueError(f"Unable to parse run number from {s!r}")


def _save_usage_data_email(usage_email: email.message.EmailMessage) -> None:
    subject = usage_email.get("Subject")
    run_number = _get_run_number_from_subject(subject)
    logger.debug(f"{subject} - {run_number}")
    # Mail extract type when implementing
    # Mail.objects.create(
    #     extract_type=ExtractTypeEnum.USAGE_DATA
    # )
    raise NotImplementedError

import logging
import os
import urllib.parse
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, MutableMapping, Optional, Tuple

from background_task import background
from background_task.models import Task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.status import HTTP_207_MULTI_STATUS, HTTP_208_ALREADY_REPORTED

from mail import requests as mail_requests
from mail.enums import ChiefSystemEnum, ReceptionStatusEnum, SourceEnum
from mail.libraries.builders import build_licence_data_mail
from mail.libraries.data_processors import build_request_mail_message_dto
from mail.libraries.lite_to_edifact_converter import EdifactValidationError
from mail.libraries.routing_controller import check_and_route_emails, send, update_mail
from mail.libraries.usage_data_decomposition import build_json_payload_from_data_blocks, split_edi_data_by_id
from mail.models import LicenceIdMapping, LicencePayload, Mail, UsageData
from mail.servers import smtp_send

logger = logging.getLogger(__name__)


MANAGE_INBOX_TASK_QUEUE = "manage_inbox_queue"
NOTIFY_USERS_TASK_QUEUE = "notify_users_queue"
LICENCE_DATA_TASK_QUEUE = "licences_updates_queue"
USAGE_FIGURES_QUEUE = "usage_figures_queue"
TASK_BACK_OFF = 3600  # Time, in seconds, to wait before scheduling a new task (used after MAX_ATTEMPTS is reached)


# Send Usage Figures to LITE API
def get_lite_api_url():
    """The URL for the licence usage callback, from the LITE_API_URL setting.

    If the configured URL has no path, use `/licences/hmrc-integration/`.
    """
    url = settings.LITE_API_URL
    components = urllib.parse.urlparse(url)

    if components.path in ("", "/"):
        components = components._replace(path="/licences/hmrc-integration/")
        url = urllib.parse.urlunparse(components)

    return url


@background(queue=USAGE_FIGURES_QUEUE, schedule=0)
def send_licence_usage_figures_to_lite_api(lite_usage_data_id):
    """Sends HMRC Usage figure updates to LITE"""

    logger.info("Preparing LITE UsageData [%s] for LITE API", lite_usage_data_id)

    try:
        lite_usage_data = UsageData.objects.get(id=lite_usage_data_id)
        licences = UsageData.licence_ids
    except UsageData.DoesNotExist:  # noqa
        _handle_exception(
            f"LITE UsageData [{lite_usage_data_id}] does not exist.",
            lite_usage_data_id,
        )
        return

    # Extract usage details of Licences issued from LITE
    _, data = split_edi_data_by_id(lite_usage_data.mail.edi_data, lite_usage_data)
    payload = build_json_payload_from_data_blocks(data)

    # We only process usage data for active licences so below error is unlikely
    if len(payload["licences"]) == 0:
        logger.error("Licences is blank in payload for %s", lite_usage_data, exc_info=True)
        return

    payload["usage_data_id"] = lite_usage_data_id
    lite_api_url = get_lite_api_url()
    logger.info("Sending LITE UsageData [%s] figures for Licences [%s] to LITE API", lite_usage_data_id, licences)

    try:
        lite_usage_data.lite_payload = payload
        lite_usage_data.save()

        response = mail_requests.put(
            lite_api_url,
            lite_usage_data.lite_payload,
            hawk_credentials=settings.HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=settings.LITE_API_REQUEST_TIMEOUT,
        )
    except Exception as exc:  # noqa
        _handle_exception(
            f"An unexpected error occurred when sending LITE UsageData [{lite_usage_data_id}] to LITE API -> "
            f"{type(exc).__name__}: {exc}",
            lite_usage_data_id,
        )
        return

    if response.status_code not in [HTTP_207_MULTI_STATUS, HTTP_208_ALREADY_REPORTED]:
        _handle_exception(
            f"An unexpected response was received when sending LITE UsageData [{lite_usage_data_id}] to "
            f"LITE API -> status=[{response.status_code}], message=[{response.text}]",
            lite_usage_data_id,
        )
        return

    if response.status_code == HTTP_207_MULTI_STATUS:
        try:
            response, accepted_licences, rejected_licences = parse_response(response)
        except Exception as exc:  # noqa
            _handle_exception(
                f"An unexpected error occurred when parsing the response for LITE UsageData "
                f"[{lite_usage_data_id}] -> {type(exc).__name__}: {exc}",
                lite_usage_data_id,
            )
            return
        save_response(lite_usage_data, accepted_licences, rejected_licences, response)

    logger.info("Successfully sent LITE UsageData [%s] to LITE API", lite_usage_data_id)


def schedule_licence_usage_figures_for_lite_api(lite_usage_data_id):
    logger.info("Scheduling UsageData '%s' for LITE API", lite_usage_data_id)
    task = Task.objects.filter(queue=USAGE_FIGURES_QUEUE, task_params=f'[["{lite_usage_data_id}"], {{}}]')

    if task.exists():
        logger.info("UsageData '%s' has already been scheduled", lite_usage_data_id)
    else:
        send_licence_usage_figures_to_lite_api(lite_usage_data_id)
        logger.info("UsageData '%s' has been scheduled", lite_usage_data_id)


def parse_response(response) -> Tuple[MutableMapping, List[str], List[str]]:
    response = response.json()
    licences = response["licences"]

    accepted_licences = [
        LicenceIdMapping.objects.get(lite_id=licence.get("id")).reference
        for licence in licences["accepted"]
        if licence.get("id")
    ]
    rejected_licences = [
        LicenceIdMapping.objects.get(lite_id=licence.get("id")).reference
        for licence in licences["rejected"]
        if licence.get("id")
    ]

    return response, accepted_licences, rejected_licences


def save_response(lite_usage_data: UsageData, accepted_licences, rejected_licences, response):
    lite_usage_data.lite_accepted_licences = accepted_licences
    lite_usage_data.lite_rejected_licences = rejected_licences
    lite_usage_data.lite_sent_at = timezone.now()
    lite_usage_data.lite_response = response

    if not lite_usage_data.has_spire_data:
        lite_usage_data.mail.status = ReceptionStatusEnum.REPLY_RECEIVED
        lite_usage_data.mail.save()

    lite_usage_data.save()


def schedule_max_tried_task_as_new_task(lite_usage_data_id):
    """
    Used to schedule a max-tried task as a new task (starting from attempts=0);
    Abstracted from 'send_licence_usage_figures_to_lite_api' to enable unit testing of a recursive operation
    """

    logger.warning(
        "Maximum attempts of %s for LITE UsageData [%s] has been reached", settings.MAX_ATTEMPTS, lite_usage_data_id
    )

    schedule_datetime = timezone.now() + timedelta(seconds=TASK_BACK_OFF)
    logger.info(
        "Scheduling new task for LITE UsageData [%s] to commence at [%s]", lite_usage_data_id, schedule_datetime
    )
    send_licence_usage_figures_to_lite_api(lite_usage_data_id, schedule=TASK_BACK_OFF)  # noqa


def _handle_exception(message, lite_usage_data_id):
    error_message = f"Failed to send LITE UsageData [{lite_usage_data_id}] to LITE API -> {message} "

    try:
        task = Task.objects.get(queue=USAGE_FIGURES_QUEUE, task_params=f'[["{lite_usage_data_id}"], {{}}]')
    except Task.DoesNotExist:
        logger.error("No task was found for UsageData [%s]", lite_usage_data_id)
    else:
        # Get the task's current attempt number by retrieving the previous attempts and adding 1
        current_attempt = task.attempts + 1

        # Schedule a new task if the current task has been attempted MAX_ATTEMPTS times;
        # HMRC Integration tasks need to be resilient and keep retrying post-failure indefinitely.
        # This logic will make MAX_ATTEMPTS attempts to send licence changes according to the Django Background Task
        # Runner scheduling, then wait TASK_BACK_OFF seconds before starting the process again.
        if current_attempt >= settings.MAX_ATTEMPTS:
            schedule_max_tried_task_as_new_task(lite_usage_data_id)

    # Raise an exception
    # this will cause the task to be marked as 'Failed' and retried if there are retry attempts left
    raise Exception(error_message)


@background(queue=LICENCE_DATA_TASK_QUEUE, schedule=0)
def send_licence_data_to_hmrc() -> Optional[bool]:
    """django-background-task version of send_licence_data_to_hmrc"""
    return send_licence_data_to_hmrc_shared()


def send_licence_data_to_hmrc_shared() -> Optional[bool]:
    """Sends LITE (or ICMS) licence updates to HMRC.

    This code is shared between two tasks currently:
      - mail/tasks -> def send_licence_data_to_hmrc (django-background-task task)
      - mail/icms/tasks -> def send_licence_data_to_hmrc (celery task)
    """

    source = SourceEnum.ICMS if settings.CHIEF_SOURCE_SYSTEM == ChiefSystemEnum.ICMS else SourceEnum.LITE
    logger.info(f"Sending {source} licence updates to HMRC")

    if Mail.objects.exclude(status=ReceptionStatusEnum.REPLY_SENT).count():
        logger.info(
            "Currently we are either waiting for a reply or next one is ready to be processed,\n"
            "so we cannot send this update now and will be picked up in the next cycle"
        )
        return

    try:
        with transaction.atomic():
            licences = LicencePayload.objects.filter(is_processed=False).select_for_update(nowait=True)

            if not licences.exists():
                logger.info("There are currently no licences to send")
                return

            mail = build_licence_data_mail(licences, source)
            mail_dto = build_request_mail_message_dto(mail)
            licence_references = [licence.reference for licence in licences]
            logger.info(
                "Created Mail [%s] with subject %s from licences [%s]", mail.id, mail_dto.subject, licence_references
            )

            send(mail_dto)
            update_mail(mail, mail_dto)

            licences.update(is_processed=True)
            logger.info("Licence references [%s] marked as processed", licence_references)

    except EdifactValidationError as err:  # noqa
        raise err
    except Exception as exc:  # noqa
        logger.error(
            "An unexpected error occurred when sending %s licence updates to HMRC -> %s",
            source,
            type(exc).__name__,
            exc_info=True,
        )
    else:
        logger.info("Successfully sent %s licences updates in Mail [%s] to HMRC", source, mail.id)
        return True


# Notify Users of Rejected Mail
@background(queue=NOTIFY_USERS_TASK_QUEUE, schedule=0)
def notify_users_of_rejected_mail(mail_id, mail_response_date):
    """If a rejected email is found, this task notifies users of the rejection"""

    logger.info("Notifying users of rejected Mail [%s, %s]", mail_id, mail_response_date)

    try:
        multipart_msg = MIMEMultipart()
        multipart_msg["From"] = settings.EMAIL_USER
        multipart_msg["To"] = ",".join(settings.NOTIFY_USERS)
        multipart_msg["Subject"] = "Mail rejected"
        body = MIMEText(f"Mail [{mail_id}] received at [{mail_response_date}] was rejected")
        multipart_msg.attach(body)

        smtp_send(multipart_msg)
    except Exception as exc:  # noqa
        error_message = (
            f"An unexpected error occurred when notifying users of rejected Mail "
            f"[{mail_id}, {mail_response_date}] -> {type(exc).__name__}: {exc}"
        )

        # Raise an exception
        # this will cause the task to be marked as 'Failed' and retried if there are retry attempts left
        raise Exception(error_message)
    else:
        logger.info("Successfully notified users of rejected Mail [%s, %s]", mail_id, mail_response_date)


# Manage Inbox


@background(queue=MANAGE_INBOX_TASK_QUEUE, schedule=0)
def manage_inbox():
    """Main task which scans inbox for SPIRE and HMRC emails"""

    logger.info("Polling inbox for updates")

    try:
        check_and_route_emails()
    except Exception as exc:  # noqa
        logger.error(
            "An unexpected error occurred when polling inbox for updates -> %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise exc


@background(queue="test_queue", schedule=0)
def emit_test_file():
    test_file_path = os.path.join(settings.BASE_DIR, ".background-tasks-is-ready")
    with open(test_file_path, "w") as test_file:
        test_file.write("OK")

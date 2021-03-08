from typing import MutableMapping, Tuple, List

import logging
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from background_task import background
from background_task.models import Task
from django.db import transaction
from django.utils import timezone
from rest_framework.status import HTTP_207_MULTI_STATUS, HTTP_208_ALREADY_REPORTED

from conf.settings import (
    EMAIL_USER,
    NOTIFY_USERS,
)
from conf.settings import (
    LITE_API_URL,
    HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
    LITE_API_REQUEST_TIMEOUT,
    MAX_ATTEMPTS,
)
from mail.enums import ReceptionStatusEnum, ReplyStatusEnum
from mail.libraries.builders import build_licence_data_mail
from mail.libraries.data_processors import build_request_mail_message_dto
from mail.libraries.mailbox_service import send_email
from mail.libraries.routing_controller import check_and_route_emails
from mail.libraries.routing_controller import update_mail, send
from mail.libraries.usage_data_decomposition import build_json_payload_from_data_blocks, split_edi_data_by_id
from mail.models import LicencePayload, Mail
from mail.models import UsageUpdate, LicenceIdMapping
from mail.requests import put
from mail.servers import MailServer

MANAGE_INBOX_TASK_QUEUE = "manage_inbox_queue"
NOTIFY_USERS_TASK_QUEUE = "notify_users_queue"
LICENCE_DATA_TASK_QUEUE = "licences_updates_queue"
USAGE_FIGURES_QUEUE = "usage_figures_queue"
TASK_BACK_OFF = 3600  # Time, in seconds, to wait before scheduling a new task (used after MAX_ATTEMPTS is reached)


# Send Usage Figures to LITE API


@background(queue=USAGE_FIGURES_QUEUE, schedule=0)
def send_licence_usage_figures_to_lite_api(lite_usage_update_id):
    """Sends HMRC Usage figure updates to LITE"""

    logging.info(f"Preparing LITE UsageUpdate [{lite_usage_update_id}] for LITE API")

    try:
        lite_usage_update = UsageUpdate.objects.get(id=lite_usage_update_id)
        licences = UsageUpdate.licence_ids
    except UsageUpdate.DoesNotExist:  # noqa
        _handle_exception(
            f"LITE UsageUpdate [{lite_usage_update_id}] does not exist.", lite_usage_update_id,
        )
        return

    logging.info(f"Sending LITE UsageUpdate [{lite_usage_update_id}] figures for Licences [{licences}] to LITE API")

    try:
        build_lite_payload(lite_usage_update)
        response = put(
            f"{LITE_API_URL}/licences/hmrc-integration/",
            lite_usage_update.lite_payload,
            hawk_credentials=HAWK_LITE_HMRC_INTEGRATION_CREDENTIALS,
            timeout=LITE_API_REQUEST_TIMEOUT,
        )
    except Exception as exc:  # noqa
        _handle_exception(
            f"An unexpected error occurred when sending LITE UsageUpdate [{lite_usage_update_id}] to LITE API -> "
            f"{type(exc).__name__}: {exc}",
            lite_usage_update_id,
        )
        return

    if response.status_code not in [HTTP_207_MULTI_STATUS, HTTP_208_ALREADY_REPORTED]:
        _handle_exception(
            f"An unexpected response was received when sending LITE UsageUpdate [{lite_usage_update_id}] to "
            f"LITE API -> status=[{response.status_code}], message=[{response.text}]",
            lite_usage_update_id,
        )
        return

    if response.status_code == HTTP_207_MULTI_STATUS:
        try:
            response, accepted_licences, rejected_licences = parse_response(response)
        except Exception as exc:  # noqa
            _handle_exception(
                f"An unexpected error occurred when parsing the response for LITE UsageUpdate "
                f"[{lite_usage_update_id}] -> {type(exc).__name__}: {exc}",
                lite_usage_update_id,
            )
            return
        save_response(lite_usage_update, accepted_licences, rejected_licences, response)

    logging.info(f"Successfully sent LITE UsageUpdate [{lite_usage_update_id}] to LITE API")


def schedule_licence_usage_figures_for_lite_api(lite_usage_update_id):
    logging.info(f"Scheduling UsageUpdate '{lite_usage_update_id}' for LITE API")
    task = Task.objects.filter(queue=USAGE_FIGURES_QUEUE, task_params=f'[["{lite_usage_update_id}"], {{}}]')

    if task.exists():
        logging.info(f"UsageUpdate '{lite_usage_update_id}' has already been scheduled")
    else:
        send_licence_usage_figures_to_lite_api(lite_usage_update_id)
        logging.info(f"UsageUpdate '{lite_usage_update_id}' has been scheduled")


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


def save_response(lite_usage_update: UsageUpdate, accepted_licences, rejected_licences, response):
    lite_usage_update.lite_accepted_licences = accepted_licences
    lite_usage_update.lite_rejected_licences = rejected_licences
    lite_usage_update.lite_sent_at = timezone.now()
    lite_usage_update.lite_response = response

    if not lite_usage_update.has_spire_data:
        lite_usage_update.mail.status = ReceptionStatusEnum.REPLY_RECEIVED
        lite_usage_update.mail.save()

    lite_usage_update.save()


def build_lite_payload(lite_usage_update: UsageUpdate):
    _, data = split_edi_data_by_id(lite_usage_update.mail.edi_data, lite_usage_update)
    payload = build_json_payload_from_data_blocks(data)
    payload["usage_update_id"] = str(lite_usage_update.id)
    lite_usage_update.lite_payload = payload
    lite_usage_update.save()


def schedule_max_tried_task_as_new_task(lite_usage_update_id):
    """
    Used to schedule a max-tried task as a new task (starting from attempts=0);
    Abstracted from 'send_licence_usage_figures_to_lite_api' to enable unit testing of a recursive operation
    """

    logging.warning(
        f"Maximum attempts of {MAX_ATTEMPTS} for LITE UsageUpdate [{lite_usage_update_id}] has been reached"
    )

    schedule_datetime = timezone.now() + timedelta(seconds=TASK_BACK_OFF)
    logging.info(
        f"Scheduling new task for LITE UsageUpdate [{lite_usage_update_id}] to commence at [{schedule_datetime}]"
    )
    send_licence_usage_figures_to_lite_api(lite_usage_update_id, schedule=TASK_BACK_OFF)  # noqa


def _handle_exception(message, lite_usage_update_id):
    error_message = f"Failed to send LITE UsageUpdate [{lite_usage_update_id}] to LITE API -> {message} "

    try:
        task = Task.objects.get(queue=USAGE_FIGURES_QUEUE, task_params=f'[["{lite_usage_update_id}"], {{}}]')
    except Task.DoesNotExist:
        logging.error(f"No task was found for UsageUpdate [{lite_usage_update_id}]")
    else:
        # Get the task's current attempt number by retrieving the previous attempts and adding 1
        current_attempt = task.attempts + 1

        # Schedule a new task if the current task has been attempted MAX_ATTEMPTS times;
        # HMRC Integration tasks need to be resilient and keep retrying post-failure indefinitely.
        # This logic will make MAX_ATTEMPTS attempts to send licence changes according to the Django Background Task
        # Runner scheduling, then wait TASK_BACK_OFF seconds before starting the process again.
        if current_attempt >= MAX_ATTEMPTS:
            schedule_max_tried_task_as_new_task(lite_usage_update_id)

    # Raise an exception
    # this will cause the task to be marked as 'Failed' and retried if there are retry attempts left
    raise Exception(error_message)


# Send Licence Updates to HMRC


@background(queue=LICENCE_DATA_TASK_QUEUE, schedule=0)
def send_licence_data_to_hmrc():
    """Sends LITE licence updates to HMRC"""

    logging.info("Sending LITE licence updates to HMRC")

    if not _is_email_slot_free():
        logging.info("There is currently an update in progress or an email is in flight")
        return

    try:
        with transaction.atomic():
            licences = LicencePayload.objects.filter(is_processed=False).select_for_update(nowait=True)

            if not licences.exists():
                logging.info("There are currently no licences to send")
                return

            mail = build_licence_data_mail(licences)
            mail_dto = build_request_mail_message_dto(mail)
            licence_references = list(licences.values_list("reference", flat=True))
            logging.info(f"Created Mail [{mail.id}] from licences [{licence_references}]")

            server = MailServer()
            send(server, mail_dto)
            update_mail(mail, mail_dto)
            licences.update(is_processed=True)
    except Exception as exc:  # noqa
        logging.error(
            f"An unexpected error occurred when sending LITE licence updates to HMRC -> {type(exc).__name__}: {exc}"
        )
    else:
        logging.info(f"Successfully sent LITE licences updates in Mail [{mail.id}] to HMRC")


def _is_email_slot_free() -> bool:
    pending_mail = _get_pending_mail()
    if pending_mail:
        logging.error(f"The following Mail is pending: {pending_mail}")
        return False

    rejected_mail = _get_rejected_mail()
    if rejected_mail:
        logging.error(f"The following Mail has been rejected: {pending_mail}")
        return False

    return True


def _get_pending_mail() -> []:
    return list(Mail.objects.exclude(status=ReceptionStatusEnum.REPLY_SENT).values_list("id", flat=True))


def _get_rejected_mail() -> []:
    return list(
        Mail.objects.filter(
            status=ReceptionStatusEnum.REPLY_SENT, response_data__icontains=ReplyStatusEnum.REJECTED,
        ).values_list("id", flat=True)
    )


# Notify Users of Rejected Mail


@background(queue=NOTIFY_USERS_TASK_QUEUE, schedule=0)
def notify_users_of_rejected_mail(mail_id, mail_response_date):
    """If a rejected email is found, this task notifies users of the rejection"""

    logging.info(f"Notifying users of rejected Mail [{mail_id}, {mail_response_date}]")

    try:
        multipart_msg = MIMEMultipart()
        multipart_msg["From"] = EMAIL_USER
        multipart_msg["To"] = ",".join(NOTIFY_USERS)
        multipart_msg["Subject"] = "Mail rejected"
        body = MIMEText(f"Mail [{mail_id}] received at [{mail_response_date}] was rejected")
        multipart_msg.attach(body)

        server = MailServer()
        smtp_connection = server.connect_to_smtp()
        send_email(smtp_connection, multipart_msg)
        server.quit_smtp_connection()
    except Exception as exc:  # noqa
        error_message = (
            f"An unexpected error occurred when notifying users of rejected Mail "
            f"[{mail_id}, {mail_response_date}] -> {type(exc).__name__}: {exc}"
        )

        # Raise an exception
        # this will cause the task to be marked as 'Failed' and retried if there are retry attempts left
        raise Exception(error_message)
    else:
        logging.info(f"Successfully notified users of rejected Mail [{mail_id}, {mail_response_date}]")


# Manage Inbox


@background(queue=MANAGE_INBOX_TASK_QUEUE, schedule=0)
def manage_inbox():
    """Main task which scans inbox for SPIRE and HMRC emails"""

    logging.info("Polling inbox for updates")

    try:
        check_and_route_emails()
    except Exception as exc:  # noqa
        logging.error(f"An unexpected error occurred when polling inbox for updates -> {type(exc).__name__}: {exc}")
        raise exc

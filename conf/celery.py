import os
from typing import TypeAlias

from celery import Celery
from celery.schedules import crontab
from dbt_copilot_python.celery_health_check import healthcheck

from mail import utils

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

app = Celery("DjangoCelery")
app.config_from_object("django.conf:settings", namespace="CELERY")

app = healthcheck.setup(app)


CELERY_SCHEDULE: TypeAlias = dict[str, dict[str, str | crontab]]


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if utils.is_production_environment():
        schedule = get_icms_prod_beat_schedule()
    else:
        schedule = get_imcs_dev_beat_schedule()

    app.conf.beat_schedule = schedule


def get_icms_prod_beat_schedule() -> CELERY_SCHEDULE:
    """Production beat schedule used when configured to run for IMCS."""

    return {
        #
        # Task to send email (icms-hmrc -> HMRC)
        "send-licence-data-to-hmrc": {
            "task": "icms:send_licence_data_to_hmrc",
            "schedule": crontab(minute="*/10"),
        },
        #
        # Task to process reply emails (HMRC -> icms-hmrc)
        "process-hmrc-emails": {
            "task": "icms:process_licence_reply_and_usage_emails",
            "schedule": crontab(minute="*/5"),
        },
        #
        # Task to forward licence reply data (icms-hmrc -> ICMS)
        "send-licence-data": {
            "task": "icms:send_licence_data_to_icms",
            "schedule": crontab(minute="*/5"),
        },
        #
        # Task to forward licence usage data (icms-hmrc -> ICMS)
        "send-usage-data": {
            "task": "icms:send_usage_data_to_icms",
            "schedule": crontab(minute="0", hour="*/2"),
        },
    }


def get_imcs_dev_beat_schedule() -> CELERY_SCHEDULE:
    """Non production beat schedule used when configured to run for ICMS.

    This schedule contains a task that will fake a response from hmrc.
    """

    return {
        "dev_process_hmrc_licence_data": {
            "task": "icms:dev_process_hmrc_licence_data",
            "schedule": crontab(minute="*/1"),
        },
        # #
        # # Task to send email (icms-hmrc -> HMRC)
        # "send-licence-data-to-hmrc": {
        #     "task": "icms:send_licence_data_to_hmrc",
        #     "schedule": crontab(minute="*/1"),
        # },
        # #
        # # Task to process reply emails (HMRC -> icms-hmrc) ** FAKE RESPONSE **
        # "process-hmrc-emails": {
        #     "task": "icms:fake_licence_reply",
        #     "schedule": crontab(minute="*/1"),
        # },
        # #
        # # Task to forward licence reply data (icms-hmrc -> ICMS)
        # "send-licence-data": {
        #     "task": "icms:send_licence_data_to_icms",
        #     "schedule": crontab(minute="*/1"),
        # },
    }


# Not used - change schedule in setup_periodic_tasks to use.
def get_test_usage_ingest_schedule() -> CELERY_SCHEDULE:
    return {
        "process-hmrc-emails": {
            "task": "icms:process_licence_reply_and_usage_emails",
            "schedule": crontab(minute="*/1"),
        },
    }

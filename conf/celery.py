import os

from celery import Celery
from celery.schedules import crontab

from mail import utils

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

app = Celery("DjangoCelery")
app.config_from_object("django.conf:settings", namespace="CELERY")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if utils.get_app_env() == "PRODUCTION":
        schedule = get_icms_prod_beat_schedule()
    else:
        schedule = get_imcs_dev_beat_schedule()

    app.conf.beat_schedule = schedule


def get_icms_prod_beat_schedule():
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
    }


def get_imcs_dev_beat_schedule():
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
def get_test_usage_ingest_schedule():
    return {
        "process-hmrc-emails": {
            "task": "icms:process_licence_reply_and_usage_emails",
            "schedule": crontab(minute="*/1"),
        },
    }

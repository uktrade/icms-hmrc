import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

from mail import utils
from mail.enums import ChiefSystemEnum

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

app = Celery("DjangoCelery")
app.config_from_object("django.conf:settings", namespace="CELERY")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if settings.CHIEF_SOURCE_SYSTEM == ChiefSystemEnum.ICMS:
        if utils.get_app_env() == "PRODUCTION":
            schedule = get_icms_prod_beat_schedule()
        else:
            schedule = get_imcs_dev_beat_schedule()

        app.conf.beat_schedule = schedule


def get_icms_prod_beat_schedule():
    """Production beat schedule used when configured to run for IMCS."""

    return {
        #
        # Task to send email (lite-hmrc -> HMRC)
        "send-licence-data-to-hmrc": {
            "task": "icms:send_licence_data_to_hmrc",
            "schedule": crontab(minute="*/10"),
        },
        #
        # Task to process reply emails (HMRC -> lite-hmrc)
        "process-hmrc-emails": {
            "task": "icms:process_licence_reply_and_usage_emails",
            "schedule": crontab(minute="*/5"),
        },
        #
        # Task to forward licence reply data (lite-hmrc -> ICMS)
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
        #
        # Task to send email (lite-hmrc -> HMRC)
        "send-licence-data-to-hmrc": {
            "task": "icms:send_licence_data_to_hmrc",
            "schedule": crontab(minute="*/1"),
        },
        #
        # Task to process reply emails (HMRC -> lite-hmrc) ** FAKE RESPONSE **
        "process-hmrc-emails": {
            "task": "icms:fake_licence_reply",
            "schedule": crontab(minute="*/1"),
        },
        #
        # Task to forward licence reply data (lite-hmrc -> ICMS)
        "send-licence-data": {
            "task": "icms:send_licence_data_to_icms",
            "schedule": crontab(minute="*/1"),
        },
    }

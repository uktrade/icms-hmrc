import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

app = Celery("DjangoCelery")
app.config_from_object("django.conf:settings", namespace="CELERY")


app.conf.beat_schedule = {
    "example-scheduled-task": {
        "task": "icms:example_task",
        "schedule": crontab(minute="*/1"),
    },
}

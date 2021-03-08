from django.apps import AppConfig
from django.db.models.signals import post_migrate

from conf.settings import BACKGROUND_TASK_ENABLED, INBOX_POLL_INTERVAL, LITE_LICENCE_DATA_POLL_INTERVAL


class MailConfig(AppConfig):
    name = "mail"

    @classmethod
    def initialize_background_tasks(cls, **kwargs):
        from background_task.models import Task
        from mail.models import UsageUpdate
        from mail.tasks import (
            MANAGE_INBOX_TASK_QUEUE,
            LICENCE_DATA_TASK_QUEUE,
            schedule_licence_usage_figures_for_lite_api,
            manage_inbox,
            send_licence_data_to_hmrc,
        )

        Task.objects.filter(queue=MANAGE_INBOX_TASK_QUEUE).delete()
        Task.objects.filter(queue=LICENCE_DATA_TASK_QUEUE).delete()

        if BACKGROUND_TASK_ENABLED:
            manage_inbox(repeat=INBOX_POLL_INTERVAL, repeat_until=None)  # noqa
            send_licence_data_to_hmrc(repeat=LITE_LICENCE_DATA_POLL_INTERVAL, repeat_until=None)  # noqa

            usage_updates_not_sent_to_lite = UsageUpdate.objects.filter(has_lite_data=True, lite_sent_at__isnull=True)
            for obj in usage_updates_not_sent_to_lite:
                schedule_licence_usage_figures_for_lite_api(str(obj.id))

    def ready(self):
        post_migrate.connect(self.initialize_background_tasks, sender=self)

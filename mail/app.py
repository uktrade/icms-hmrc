from django.apps import AppConfig
from django.db.models.signals import post_migrate

from conf.settings import INBOX_POLL_INTERVAL, LITE_LICENCE_UPDATE_POLL_INTERVAL


class MailConfig(AppConfig):
    name = "mail"

    @classmethod
    def initialize_background_tasks(cls, **kwargs):
        from background_task.models import Task
        from mail.tasks import email_lite_licence_updates, manage_inbox_queue

        Task.objects.filter(task_name="mail.tasks.email_lite_licence_updates").delete()
        email_lite_licence_updates(repeat=LITE_LICENCE_UPDATE_POLL_INTERVAL, repeat_until=None)  # noqa

        Task.objects.filter(task_name="mail.tasks.manage_inbox_queue").delete()
        manage_inbox_queue(repeat=INBOX_POLL_INTERVAL, repeat_until=None)  # noqa

    def ready(self):
        post_migrate.connect(self.initialize_background_tasks, sender=self)

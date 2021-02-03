from django.apps import AppConfig
from django.db.models.signals import post_migrate


class MockHmrcConfig(AppConfig):
    name = "mock_hmrc"

    @classmethod
    def initialize_background_tasks(cls, **kwargs):
        pass

    def ready(self):
        post_migrate.connect(self.initialize_background_tasks, sender=self)

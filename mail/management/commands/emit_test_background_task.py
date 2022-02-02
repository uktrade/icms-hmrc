from django.core.management import BaseCommand

from mail.tasks import emit_test_file


class Command(BaseCommand):
    """
    pipenv run ./manage.py emit_test_background_task
    """

    def handle(self, *args, **options):
        emit_test_file()

import json
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mail import requests as mail_requests


# To run: make manage args="check_icms_connection"
class Command(BaseCommand):
    help = """Test ICMS-HMRC can send a request to ICMS server."""

    def handle(self, *args, **options):
        self.stdout.write("Checking ICMS connection.")

        url = urljoin(settings.ICMS_API_URL, "chief/check-icms-connection/")
        data = {"foo": "bar"}

        response: requests.Response = mail_requests.post(
            url,
            data,
            hawk_credentials=settings.ICMS_API_ID,
            timeout=settings.ICMS_API_REQUEST_TIMEOUT,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            self.stderr.write(str(response.content))
            raise e

        response_content = json.loads(response.content.decode("utf-8"))

        if response_content != {"bar": "foo"}:
            raise CommandError(f"Invalid response from ICMS: {response_content}")

        self.stdout.write("ICMS-HMRC can communicate with ICMS using mohawk.", self.style.SUCCESS)

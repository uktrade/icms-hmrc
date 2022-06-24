from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status


# override_settings doesn't work - left here for reference
# @override_settings(HAWK_AUTHENTICATION_ENABLED=True)
@patch("conf.authentication.hawk_authentication_enabled", lambda: True)
class TestHawkAuthentication(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # test endpoint that retrieves licence details
        cls.test_url = reverse("mail:licence")

    def test_hawk_authentication_returns_401(self):
        resp = self.client.get(self.test_url)

        # This will trigger an unknown Exception (as HTTP_HAWK_AUTHENTICATION isn't set)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # This will trigger a HawkException as HTTP_HAWK_AUTHENTICATION is invalid
        hawk_header = 'Hawk mac="", hash="", id="lite-api", ts="", nonce=""'
        resp = self.client.get(self.test_url, HTTP_HAWK_AUTHENTICATION=hawk_header)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

from django.test import TestCase

from mail.tasks import get_lite_api_url


class GetLiteAPIUrlTests(TestCase):
    def test_get_url_with_no_path(self):
        with self.settings(LITE_API_URL="https://example.com"):
            result = get_lite_api_url()

        self.assertEqual(result, "https://example.com/licences/hmrc-integration/")

    def test_get_url_with_root_path(self):
        with self.settings(LITE_API_URL="https://example.com/"):
            result = get_lite_api_url()

        self.assertEqual(result, "https://example.com/licences/hmrc-integration/")

    def test_get_url_with_path_from_setting(self):
        with self.settings(LITE_API_URL="https://example.com/foo"):
            result = get_lite_api_url()

        self.assertEqual(result, "https://example.com/foo")

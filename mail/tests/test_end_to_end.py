from urllib.parse import quote

import requests
from django.conf import settings
from django.core import mail
from django.urls import reverse

from mail.tests.libraries.client import LiteHMRCTestClient


class EndToEndTests(LiteHMRCTestClient):
    def get_smtp_body(self):
        message = mail.outbox[0].message()
        # We now have a SafeMIMEMultipart object, and can get each MIME part.
        # First part is an empty body (no idea why), we want the second.
        attachment = message.get_payload(1)

        return attachment.get_payload()

    def test_send_email_to_hmrc_e2e(self):
        self.client.get(reverse("mail:set_all_to_reply_sent"))
        self.client.post(
            reverse("mail:update_licence"), data=self.licence_payload_json, content_type="application/json"
        )
        response = self.client.get(reverse("mail:send_updates_to_hmrc"))
        body = self.get_smtp_body().replace("\r", "")
        ymdhm_timestamp = body.split("\n")[0].split("\\")[5]
        run_number = body.split("\n")[0].split("\\")[6]
        expected_mail_body = fr"""1\fileHeader\SPIRE\CHIEF\licenceData\{ymdhm_timestamp}\{run_number}\N
2\licence\20200000001P\insert\GBSIEL/2020/0000001/P\SIE\E\20200602\20220602
3\trader\\GB123456789000\20200602\20220602\Organisation\might\248 James Key Apt. 515\Apt. 942\West Ashleyton\Farnborough\GU40 2LX
4\country\GB\\D
5\foreignTrader\End User\42 Road, London, Buckinghamshire\\\\\\GB
6\restrictions\Provisos may apply please see licence
7\line\1\\\\\Sporting shotgun\Q\\030\\10\\\\\\
8\end\licence\7
9\fileTrailer\1
"""
        assert body == expected_mail_body  # nosec
        encoded_reference_code = quote("GBSIEL/2020/0000001/P", safe="")
        response = self.client.get(f"{reverse('mail:licence')}?id={encoded_reference_code}")
        assert response.json()["status"] == "reply_pending"  # nosec

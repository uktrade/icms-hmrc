from django.conf import settings
from django.test import testcases
from django.utils import timezone

from mail.chief.email import EmailMessageData, build_email_message


class BuildEmailMessageTest(testcases.TestCase):
    maxDiff = None

    def test_build_email_message(self):
        attachment = "30 \U0001d5c4\U0001d5c6/\U0001d5c1 \u5317\u4EB0"
        email_message_dto = EmailMessageData(
            run_number=1,
            sender="This...gets....ignored ¯\\_(ツ)_//¯",
            receiver="receiver@email_domain.com",
            date=timezone.now(),
            body=None,
            subject="Some subject",
            attachment=["some filename", attachment],
        )

        mime_multipart = build_email_message(email_message_dto)
        mime_multipart.set_boundary("===============8537751789001939036==")

        self.assertEqual(
            mime_multipart.as_string(),
            (
                'Content-Type: multipart/mixed; boundary="===============8537751789001939036=="\n'
                "MIME-Version: 1.0\n"
                f"From: {settings.EMAIL_HOST_USER}\n"
                f"To: receiver@email_domain.com\n"
                "Subject: Some subject\n"
                "name: Some subject\n\n"
                "--===============8537751789001939036==\n"
                'Content-Type: text/plain; charset="iso-8859-1"\n'
                "MIME-Version: 1.0\n"
                "Content-Transfer-Encoding: quoted-printable\n\n"
                "\n\n\n"
                "--===============8537751789001939036==\n"
                "Content-Type: application/octet-stream\n"
                "MIME-Version: 1.0\n"
                "Content-Transfer-Encoding: base64\n"
                'Content-Disposition: attachment; filename="some filename"\n'
                "Content-Transfer-Encoding: 7bit\n"
                "name: Some subject\n\n"
                "30 km/h Bei Jing \n"
                "--===============8537751789001939036==--\n"
            ),
        )

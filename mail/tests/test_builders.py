from django.conf import settings
from django.test import testcases

from mail.libraries import builders
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import read_file


class BuildEmailMessageTest(testcases.TestCase):
    def test_build_email_message(self):
        attachment = "30 \U0001d5c4\U0001d5c6/\U0001d5c1 \u5317\u4EB0"
        email_message_dto = EmailMessageDto(
            run_number=1,
            sender=settings.HMRC_ADDRESS,
            receiver=settings.SPIRE_ADDRESS,
            body=None,
            subject="Some subject",
            attachment=["some filename", attachment],
            raw_data="",
        )

        mime_multipart = builders.build_email_message(email_message_dto)
        mime_multipart.set_boundary("===============8537751789001939036==")

        self.assertEqual(
            mime_multipart.as_string(),
            (
                'Content-Type: multipart/mixed; boundary="===============8537751789001939036=="\n'
                "MIME-Version: 1.0\n"
                f"From: {settings.EMAIL_USER}\n"
                f"To: {settings.SPIRE_ADDRESS}\n"
                "Subject: Some subject\n\n"
                "--===============8537751789001939036==\n"
                "Content-Type: application/octet-stream\n"
                "MIME-Version: 1.0\n"
                "Content-Transfer-Encoding: base64\n"
                "Content-Disposition: attachment; filename= some filename\n"
                "Content-Transfer-Encoding: 7bit\n\n"
                "30 km/h Bei Jing \n"
                "--===============8537751789001939036==--\n"
            ),
        )

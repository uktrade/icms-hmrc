from django.http import JsonResponse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from conf.settings import EMAIL_PASSWORD
from mail.services.data_processing import (
    process_and_save_email_message,
    collect_and_send_data_to_dto,
)
from mail.servers import MailServer
from mail.services.MailboxService import MailboxService
from mail.builders import build_text_message
from mail.dtos import to_json


# Leaving the endpoints in place for now for testing purposes
class SendMailView(APIView):
    def get(self, request):
        server = MailServer(
            hostname="localhost",
            user="test18",
            pwd=EMAIL_PASSWORD,
            pop3_port=995,
            smtp_port=587,
        )
        smtp_conn = server.connect_smtp()
        mailBoxService = MailboxService()
        mailBoxService.send_email(
            smtp_conn, build_text_message("junk@mail.com", "junk2@mail.com")
        )
        smtp_conn.quit()
        return JsonResponse(status=HTTP_200_OK, data={"message": "email_sent !"})


class ReadMailView(APIView):
    def get(self, request):
        server = MailServer(
            hostname="localhost",
            user="test18",
            pwd=EMAIL_PASSWORD,
            pop3_port=995,
            smtp_port=587,
        )
        pop3_conn = server.connect_pop3()
        mailBoxService = MailboxService()
        last_msg_dto = mailBoxService.read_last_message(pop3_conn)
        pop3_conn.quit()
        return JsonResponse(status=HTTP_200_OK, data=to_json(last_msg_dto), safe=False)


class RouteMailView(APIView):
    def get(self, request):
        server = MailServer(
            hostname="localhost",
            user="test18",
            pwd=EMAIL_PASSWORD,
            pop3_port=995,
            smtp_port=587,
        )
        pop3_conn = server.connect_pop3()
        mail_box_service = MailboxService()
        last_msg_dto = mail_box_service.read_last_message(pop3_conn)
        pop3_conn.quit()
        # todo
        # TODO: Process data (saves data to db from dto)
        if not process_and_save_email_message(last_msg_dto):
            return JsonResponse(
                status=HTTP_400_BAD_REQUEST, data={"errors": "Bad data"}
            )
        # mail_box_service.handle_run_number(last_msg_dto) this should go into the process part
        # TODO: Collect data (retrieves data from db back into dto) return -> message_to_send_dto
        message_to_send_dto = collect_and_send_data_to_dto()
        smtp_conn = server.connect_smtp()
        # todo
        mail_box_service.send_email(smtp_conn, self.build_msg(message_to_send_dto))

        resp_msg = "Email routed from {} to {}".format(
            last_msg_dto.sender, "receiver tbd"
        )
        return JsonResponse(status=HTTP_200_OK, data={"message": resp_msg}, safe=False)

    def build_msg(self, email_message_dto):
        pass

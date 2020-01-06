from django.http import JsonResponse
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from mail.helpers import build_and_send_message
from mail.servers import MailServer


# Leaving the endpoints in place for now for testing purposes
class SendMailView(APIView):
    def get(self, request):
        sender = "junk@mail.com"
        receiver = "junk2@mail.com"
        server = MailServer()
        build_and_send_message(server, sender, receiver)
        return JsonResponse(status=HTTP_200_OK, data={"message": "email_sent !"})


class ReadMailView(APIView):
    def get(self, request):
        server = MailServer()
        last_msg = server.read_email()
        return JsonResponse(status=HTTP_200_OK, data=last_msg, safe=False)


def job():
    # Job called by schedule job
    server = MailServer()
    last_message = server.read_email()
    # TODO: Some logic which does the following:
    #   - reads the 'last_message'
    #   - Saves the message in a table (against a sent message if it is a reply)
    #   - Reads the sender
    #   - Records run number and if required and adjusts run number
    #   - calls build_and_send_message with new receiver address (keep the sender)
    #   - records the send message in table

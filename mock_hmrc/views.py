from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView

from mock_hmrc.tasks import handle_replies

# Create your views here.


class HandleReplies(APIView):
    def get(self, request):
        handle_replies.now()

        return HttpResponse(status=status.HTTP_200_OK)

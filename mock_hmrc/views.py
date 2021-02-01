from rest_framework.views import APIView

from conf.authentication import HawkOnlyAuthentication

# Create your views here.

class HandleReplies(APIView):
    authentication_classes = HawkOnlyAuthentication

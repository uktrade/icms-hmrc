import logging
import time
import uuid


class LoggingMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        request.correlation = uuid.uuid4().hex
        data = {
            "message": "unpopped popcorn lite hmrc",
            "corrID": request.correlation,
            "type": "http request",
            "method": request.method,
            "url": request.path,
        }
        response = self.get_response(request)
        data["type"] = "http response"
        data["elapsed_time"] = time.time() - start
        logging.info(data)
        return response

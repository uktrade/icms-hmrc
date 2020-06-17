import logging
import time
import uuid

from mohawk import Receiver
from mohawk.util import prepare_header_val, utc_now


class LoggingMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        correlation = None
        start = time.time()
        if "HTTP_X_CORRELATION_ID" in request.META:
            correlation = request.META["HTTP_X_CORRELATION_ID"]
        request.correlation = correlation or uuid.uuid4().hex
        response = self.get_response(request)
        logging.info(
            {
                "message": "liteolog hmrc",
                "corrID": request.correlation,
                "type": "http response",
                "method": request.method,
                "url": request.path,
                "elapsed_time": time.time() - start,
            }
        )

        return response


class HawkSigningMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Sign response
        if hasattr(request, "auth") and isinstance(request.auth, Receiver):
            # Get mohawk to produce the header for the response
            response_header = request.auth.respond(content=response.content, content_type=response["Content-Type"])

            # Manually add in the nonce we were called with and the current date/time as timestamp.  HMRC Integration
            # does not expect clients to validate the nonce, these values are included to workaround an issue
            # in mohawk that meant a nonce checking warning was being unavoidably logged on the client side
            response_header = '{header}, nonce="{nonce}"'.format(
                header=response_header, nonce=prepare_header_val(request.auth.parsed_header["nonce"]),
            )
            response_header = '{header}, ts="{nonce}"'.format(
                header=response_header, nonce=prepare_header_val(str(utc_now()))
            )

            response["Server-Authorization"] = response_header

        return response

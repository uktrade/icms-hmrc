import threading
import time
from datetime import datetime

from mail.routing_controller import check_and_route_emails


def scheduled_job():
    # Do some stuff
    # Offload the blocking job to a new thread

    t = threading.Thread(target=some_fn, args=(True,))
    t.setDaemon(True)
    t.start()

    return True


def some_fn(x):
    while x:
        if not x:
            check_and_route_emails()
        print(datetime.now())
        # if condition:
        #     return
        # else:
        #     time.sleep(interval in seconds)
        # return 0
        time.sleep(5)

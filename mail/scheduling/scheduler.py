import logging
import threading
import time

from conf.settings import POLL_INTERVAL


def scheduled_job():
    t = threading.Thread(target=polling_job, args=(True,))
    t.setDaemon(True)
    t.start()

    return True


def polling_job(x):
    while x:
        from mail.routing_controller import check_and_route_emails

        try:
            check_and_route_emails()
        except Exception as e:  # noqa
            logging.info({"message": "liteolog hmrc", "status": "Exception: " + str(e)})
        time.sleep(int(POLL_INTERVAL))

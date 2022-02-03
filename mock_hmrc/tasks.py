import logging

from background_task import background

from mock_hmrc.handler import parse_and_reply_emails


@background(queue="handle_hmrc_replies_queue", schedule=0)
def handle_replies():
    logging.info("Polling mock HMRC inbox for updates")

    try:
        parse_and_reply_emails()
    except Exception as exc:  # noqa
        logging.error(
            "An unexpected error occurred when polling inbox for updates -> %s", type(exc).__name__, exc_info=True,
        )
        raise exc

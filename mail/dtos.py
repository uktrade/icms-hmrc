from collections import namedtuple
import logging

log = logging.getLogger(__name__)

EmailMessageDto = namedtuple("EmailMessageDto", "sender, subject, body, attachment")

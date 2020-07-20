from collections import namedtuple

EmailMessageDto = namedtuple("EmailMessageDto", "run_number, sender, receiver, subject, body, attachment, raw_data")

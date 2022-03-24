from collections import namedtuple

EmailMessageDto = namedtuple(
    "EmailMessageDto", "run_number, sender, receiver, date, subject, body, attachment, raw_data"
)

HmrcEmailMessageDto = namedtuple(
    "HmrcEmailMessageDto", "run_number, message_id, sender, receiver, subject, body, attachment, raw_data"
)

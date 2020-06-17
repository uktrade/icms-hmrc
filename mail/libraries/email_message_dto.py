import json
from collections import namedtuple

EmailMessageDto = namedtuple("EmailMessageDto", "run_number, sender, receiver, subject, body, attachment, raw_data")


def to_json(email_message_dto: EmailMessageDto) -> dict:
    """Converts EmailMessageDto to JSON str
    :param email_message_dto: an object of type EmailMessageDto
    :return: str in JSON format
    """
    if email_message_dto is None:
        raise TypeError("given EmailMessageDto is invalid!")

    if email_message_dto.attachment is None or not isinstance(email_message_dto.attachment[1], bytes):
        raise TypeError("Invalid attribute 'attachment'")

    _dict = {
        "run_number": email_message_dto.run_number,
        "sender": email_message_dto.sender,
        "subject": email_message_dto.subject,
        "receiver": email_message_dto.receiver,
        "body": email_message_dto.body,
        "attachment": {"name": email_message_dto.attachment[0], "data": _jsonize(email_message_dto.attachment[1]),},
        "raw_data": _jsonize(email_message_dto.raw_data[1]),
    }
    return json.dumps(_dict)


def to_logs(email_message_dto: EmailMessageDto):
    return {
        "dto": {
            "run_number": email_message_dto.run_number,
            "sender": email_message_dto.sender,
            "subject": email_message_dto.subject,
            "receiver": email_message_dto.receiver,
            "body": email_message_dto.body,
            "attachment": {"name": email_message_dto.attachment[0], "data": email_message_dto.attachment[1][0:50]},
            "raw_data": str(email_message_dto.raw_data[0:50]),
        }
    }


def _jsonize(data):
    return data.decode("ASCII") if isinstance(data, bytes) else data

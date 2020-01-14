from collections import namedtuple
import json

EmailMessageDto = namedtuple(
    "EmailMessageDto",
    "run_number, sender, receiver, subject, body, attachment, raw_data",
)


def to_json(email_message_dto: EmailMessageDto):
    """
    Converts EmailMessageDto to JSON str
    :param email_message_dto: an object of type EmailMessageDto
    :return: str in JSON format
    """
    if email_message_dto is None:
        raise TypeError("given EmailMessageDto is invalid!")

    if email_message_dto.attachment is None or not isinstance(
        email_message_dto.attachment[1], bytes
    ):
        raise TypeError("Invalid attribute 'attachment'")

    email_message_dto.attachment[1] = email_message_dto.attachment[1].decode("ascii")
    _dict = {
        "run_number": email_message_dto.run_number,
        "sender": email_message_dto.sender,
        "subject": email_message_dto.subject,
        "receiver": email_message_dto.receiver,
        "body": email_message_dto.body,
        "attachment": {
            "name": email_message_dto.attachment[0],
            "data": email_message_dto.attachment[1],
        },
        "raw_data": str(email_message_dto.raw_data[1]),
    }
    return json.dumps(_dict)

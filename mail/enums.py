class ReceptionStatusEnum:
    PENDING = "pending"
    REPLY_PENDING = "reply_pending"
    REPLY_RECEIVED = "reply_received"
    REPLY_SENT = "reply_sent"

    choices = [
        (PENDING, "Pending"),
        (REPLY_PENDING, "Reply Pending"),
        (REPLY_RECEIVED, "Reply Received"),
        (REPLY_SENT, "Reply Sent"),
    ]

    @classmethod
    def get_text(cls, status):
        for k, v in cls.choices:
            if status == k:
                return v

    @classmethod
    def as_list(cls):
        return [{"status": choice[0]} for choice in cls.choices]


class ExtractTypeEnum:
    USAGE_UPDATE = "usage_update"
    USAGE_REPLY = "usage_reply"
    LICENCE_UPDATE = "licence_update"
    LICENCE_REPLY = "licence_reply"

    choices = [
        (USAGE_UPDATE, "Usage update"),
        (USAGE_REPLY, "Usage Reply"),
        (LICENCE_UPDATE, "Licence Update"),
        (LICENCE_REPLY, "Licence Reply"),
    ]

    email_keys = [
        ("usageData", USAGE_UPDATE),
        ("usageReply", USAGE_REPLY),
        ("licenceUpdate", LICENCE_UPDATE),
        ("licenceReply", LICENCE_REPLY),
    ]

    @classmethod
    def get_text(cls, _type):
        for k, v in cls.choices:
            if _type == k:
                return v

    @classmethod
    def as_list(cls):
        return [{"extract_type": choice[0]} for choice in cls.choices]


class SourceEnum:
    SPIRE = "SPIRE"
    LITE = "LITE"
    HMRC = "HMRC"

    choices = [
        (SPIRE, "SPIRE"),
        (LITE, "LITE"),
        (HMRC, "HMRC"),
    ]

    @classmethod
    def as_list(cls):
        return [{"status": choice[0]} for choice in cls.choices]

class LicenceActionEnum:
    INSERT = "insert"
    CANCEL = "cancel"
    UPDATE = "update"

    choices = [
        (INSERT, "Insert"),
        (CANCEL, "Cancel"),
        (UPDATE, "Update"),
    ]

    @classmethod
    def get_text(cls, status) -> str:
        for k, v in cls.choices:
            if status == k:
                return v

    @classmethod
    def as_list(cls) -> list:
        return [{"status": choice[0]} for choice in cls.choices]


class LicenceTypeEnum:
    SIEL = "siel"
    SICL = "sicl"
    SITL = "sitl"
    OIEL = "oiel"
    OICL = "oicl"
    OGEL = "ogel"
    OGCL = "ogcl"
    OGTL = "ogtl"

    choices = [
        (SIEL, "Standard Individual Export Licence"),
        (SICL, "Standard Individual Trade Control Licence"),
        (SITL, "Standard Individual Transhipment Licence"),
        (OIEL, "Open Individual Export Licence"),
        (OICL, "Open Individual Trade Control Licence"),
        (OGEL, "Open General Export Licence"),
        (OGCL, "Open General Trade Control Licence"),
        (OGTL, "Open General Transhipment Licence"),
    ]

    @classmethod
    def get_text(cls, status) -> str:
        for k, v in cls.choices:
            if status == k:
                return v

    @classmethod
    def as_list(cls) -> list:
        return [{"status": choice[0]} for choice in cls.choices]

    STANDARD_LICENCES = [SIEL, SICL, SITL]
    OPEN_LICENCES = [OIEL, OICL]
    OPEN_GENERAL_LICENCES = [OGEL, OGCL, OGTL]


class ReplyStatusEnum:
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"

    choices = [
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (PENDING, "Pending"),
    ]

    @classmethod
    def get_text(cls, status) -> str:
        for k, v in cls.choices:
            if status == k:
                return v

    @classmethod
    def as_list(cls) -> list:
        return [{"status": choice[0]} for choice in cls.choices]


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
    def as_list(cls) -> list:
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
    def get_text(cls, _type) -> str:
        for k, v in cls.choices:
            if _type == k:
                return v

    @classmethod
    def as_list(cls) -> list:
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
    def as_list(cls) -> list:
        return [{"status": choice[0]} for choice in cls.choices]


class UnitMapping:
    number = 30
    gram = 21
    kilogram = 23
    meters_squared = 45
    meters = 57
    litre = 94
    meters_cubed = 2
    intangible = 30

    choices = [
        (number, "NAR"),
        (gram, "GRM"),
        (kilogram, "KGM"),
        (meters_squared, "MTK"),
        (meters, "MTR"),
        (litre, "LTR"),
        (meters_cubed, "MTQ"),
        (intangible, "ITG"),
    ]

    @classmethod
    def convert(cls, unit) -> int:
        for k, v in cls.choices:
            if unit == v:
                return k

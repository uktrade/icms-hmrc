# Temporary values, THESE ARE NOT CORRECT OR FINAL


class ReceptionStatusEnum:
    ACCEPTED = "accepted"

    choices = [
        (ACCEPTED, "Accepted"),
    ]

    @classmethod
    def human_readable(cls, status):
        for k, v in cls.choices:
            if status == k:
                return v

    @classmethod
    def as_list(cls):
        return [{"status": choice[0]} for choice in cls.choices]


class ExtractTypeEnum:
    INSERT = "insert"

    choices = [
        (INSERT, "Insert"),
    ]

    @classmethod
    def human_readable(cls, status):
        for k, v in cls.choices:
            if status == k:
                return v

    @classmethod
    def as_list(cls):
        return [{"extract_type": choice[0]} for choice in cls.choices]


class SourceEnum:
    SPIRE = "SPIRE"
    LITE = "LITE"

    choices = [(SPIRE, "SPIRE"), (LITE, "LITE")]

    @classmethod
    def as_list(cls):
        return [{"status": choice[0]} for choice in cls.choices]

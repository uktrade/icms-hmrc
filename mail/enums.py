import enum
from types import DynamicClassAttribute

from django.utils.functional import Promise, classproperty


# Backported from Django 4.x
# https://github.com/django/django/blob/9c19aff7c/django/db/models/enums.py  /PS-IGNORE
class ChoicesMeta(enum.EnumMeta):
    """A metaclass for creating a enum choices."""

    def __new__(metacls, classname, bases, classdict, **kwds):
        labels = []
        for key in classdict._member_names:
            value = classdict[key]
            if isinstance(value, (list, tuple)) and len(value) > 1 and isinstance(value[-1], (Promise, str)):
                *value, label = value
                value = tuple(value)
            else:
                label = key.replace("_", " ").title()
            labels.append(label)
            # Use dict.__setitem__() to suppress defenses against double
            # assignment in enum's classdict.
            dict.__setitem__(classdict, key, value)
        cls = super().__new__(metacls, classname, bases, classdict, **kwds)
        for member, label in zip(cls.__members__.values(), labels):
            member._label_ = label
        return enum.unique(cls)

    def __contains__(cls, member):
        if not isinstance(member, enum.Enum):
            # Allow non-enums to match against member values.
            return any(x.value == member for x in cls)
        return super().__contains__(member)

    @property
    def names(cls):
        empty = ["__empty__"] if hasattr(cls, "__empty__") else []
        return empty + [member.name for member in cls]

    @property
    def choices(cls):
        empty = [(None, cls.__empty__)] if hasattr(cls, "__empty__") else []
        return empty + [(member.value, member.label) for member in cls]

    @property
    def labels(cls):
        return [label for _, label in cls.choices]

    @property
    def values(cls):
        return [value for value, _ in cls.choices]


class Choices(enum.Enum, metaclass=ChoicesMeta):
    """Class for creating enumerated choices."""

    @DynamicClassAttribute
    def label(self):
        return self._label_

    @property
    def do_not_call_in_templates(self):
        return True

    def __str__(self):
        """
        Use value when cast to str, so that Choices set as model instance
        attributes are rendered as expected in templates and similar contexts.
        """
        return str(self.value)

    # A similar format was proposed for Python 3.10.
    def __repr__(self):
        return f"{self.__class__.__qualname__}.{self._name_}"


class IntegerChoices(int, Choices):
    """Class for creating enumerated integer choices."""

    pass


class TextChoices(str, Choices):
    """Class for creating enumerated string choices."""

    def _generate_next_value_(name, start, count, last_values):
        return name


class LicenceActionEnum(TextChoices):
    INSERT = "insert"
    CANCEL = "cancel"
    UPDATE = "update"


# Django's choices don't support groups, so we are using @classproperty.
class LicenceTypeEnum(TextChoices):
    SIEL = "siel", "Standard Individual Export Licence"
    SICL = "sicl", "Standard Individual Trade Control Licence"
    SITL = "sitl", "Standard Individual Transhipment Licence"
    OIEL = "oiel", "Open Individual Export Licence"
    OICL = "oicl", "Open Individual Trade Control Licence"
    OGEL = "ogel", "Open General Export Licence"
    OGCL = "ogcl", "Open General Trade Control Licence"
    OGTL = "ogtl", "Open General Transhipment Licence"

    # ICMS Licence types
    IMPORT_DFL = "DFL", "Deactivated Firearms Licence"
    IMPORT_OIL = "OIL", "Open Individual Import Licence"
    IMPORT_SIL = "SIL", "Specific Individual Import Licence"

    @classproperty
    def STANDARD_LICENCES(cls):
        return [cls.SIEL, cls.SICL, cls.SITL]

    @classproperty
    def OPEN_LICENCES(cls):
        return [cls.OIEL, cls.OICL]

    @classproperty
    def OPEN_GENERAL_LICENCES(cls):
        return [cls.OGEL, cls.OGCL, cls.OGTL]


LITE_HMRC_LICENCE_TYPE_MAPPING = {
    LicenceTypeEnum.SIEL.value: "SIE",
    LicenceTypeEnum.SICL.value: "SIE",
    LicenceTypeEnum.SITL.value: "SIE",
    LicenceTypeEnum.OIEL.value: "OIE",
    # No OICL?
    LicenceTypeEnum.OGEL.value: "OGE",
    LicenceTypeEnum.OGCL.value: "OGE",
    LicenceTypeEnum.OGTL.value: "OGE",
    # ICMS Licence types
    LicenceTypeEnum.IMPORT_DFL.value: "SIL",
    LicenceTypeEnum.IMPORT_OIL.value: "OIL",
    LicenceTypeEnum.IMPORT_SIL.value: "SIL",
}


class ReplyStatusEnum(TextChoices):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"


class ReceptionStatusEnum(TextChoices):
    PENDING = "pending"
    REPLY_PENDING = "reply_pending"
    REPLY_RECEIVED = "reply_received"
    REPLY_SENT = "reply_sent"


class ExtractTypeEnum(TextChoices):
    USAGE_DATA = "usage_data"
    USAGE_REPLY = "usage_reply"
    LICENCE_REPLY = "licence_reply"
    LICENCE_DATA = "licence_data"

    @classproperty
    def email_keys(cls):
        return [
            ("usageData", cls.USAGE_DATA.value),
            ("usageReply", cls.USAGE_REPLY.value),
            ("licenceReply", cls.LICENCE_REPLY.value),
            ("licenceData", cls.LICENCE_DATA.value),
        ]


class SourceEnum(TextChoices):
    SPIRE = "SPIRE", "SPIRE"
    LITE = "LITE", "LITE"
    HMRC = "HMRC", "HMRC"
    ICMS = "ICMS", "ICMS"


# System names recognised by CHIEF
class ChiefSystemEnum(TextChoices):
    ICMS = "ILBDOTI"
    SPIRE = "SPIRE"


# We want a duplicate entry for ITG, so cannot use Django's enum.
class UnitMapping(enum.Enum):
    NAR = 30  # number
    GRM = 21  # gram
    KGM = 23  # kilogram
    MTK = 45  # meters_squared
    MTR = 57  # meters
    LTR = 94  # litre
    MTQ = 2  # meters_cubed
    ITG = 30  # intangible

    @classmethod
    def serializer_choices(cls):
        # Used by the API serializer for validation.
        return list(cls.__members__.keys())


class MailReadStatuses(TextChoices):
    READ = "READ"
    UNREAD = "UNREAD"
    UNPROCESSABLE = "UNPROCESSABLE"


class LicenceStatusEnum(TextChoices):
    OPEN = "open"
    EXHAUST = "exhaust"
    SURRENDER = "surrender"
    EXPIRE = "expire"
    CANCEL = "cancel"

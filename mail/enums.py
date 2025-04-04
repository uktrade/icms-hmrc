import enum

from django.db.models import IntegerChoices, TextChoices


class LicenceActionEnum(TextChoices):
    INSERT = "insert"
    CANCEL = "cancel"
    REPLACE = "replace"
    # Not supported by ICMS
    # UPDATE = "update"


class LicenceTypeEnum(TextChoices):
    IMPORT_DFL = "DFL", "Deactivated Firearms Licence"
    IMPORT_OIL = "OIL", "Open Individual Import Licence"
    IMPORT_SIL = "SIL", "Specific Individual Import Licence"
    IMPORT_SAN = "SAN", "Sanctions and Adhoc Import Licence"
    IMPORT_NUCLEAR = "NUCLEAR", "Nuclear Material Import Licence"


ICMS_HMRC_LICENCE_TYPE_MAPPING = {
    LicenceTypeEnum.IMPORT_DFL.value: "SIL",
    LicenceTypeEnum.IMPORT_OIL.value: "OIL",
    LicenceTypeEnum.IMPORT_SIL.value: "SIL",
    LicenceTypeEnum.IMPORT_SAN.value: "SAN",
    LicenceTypeEnum.IMPORT_NUCLEAR.value: "SIL",
}


class MailStatusEnum(TextChoices):
    PENDING = "pending"
    REPLY_PENDING = "reply_pending"
    REPLY_RECEIVED = "reply_received"
    REPLY_PARTIALLY_PROCESSED = "reply_partially_processed"
    REPLY_PROCESSED = "reply_processed"


class ExtractTypeEnum(TextChoices):
    USAGE_DATA = "usage_data"
    USAGE_REPLY = "usage_reply"
    LICENCE_REPLY = "licence_reply"
    LICENCE_DATA = "licence_data"


class SourceEnum(TextChoices):
    HMRC = "HMRC", "HMRC"
    ICMS = "ICMS", "ICMS"


# System names recognised by CHIEF
class ChiefSystemEnum(TextChoices):
    ICMS = "ILBDOTI"


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


# Chief "controlledBy" field
class ControlledByEnum(TextChoices):
    VALUE_AND_QUANTITY = "B", "Both Value and Quantity"
    OPEN = "O", "Open (no usage recording or control)"
    QUANTITY = "Q", "Quantity Only"
    VALUE = "V", "Value Only"


# Chief "quantityUnit" field
# https://www.gov.uk/government/publications/uk-trade-tariff-quantity-codes/uk-trade-tariff-quantity-codes
class QuantityCodeEnum(IntegerChoices):
    """Quantity codes known by HMRC.

    Only values seen in ICMS have been enabled - Uncomment others as required.
    """

    # 1. Weight
    # Ounce = 11, "Ounce"
    # Pound = 12, "Pound"
    # Cental (100lb) = 13, "Cental (100lb)"
    # Cwt = 14, "Cwt"
    # 1,000lb = 15, "1,000lb"
    # Ton = 16, "Ton"
    # Oz Troy = 17, "Oz Troy"
    # Lb Troy = 18, "Lb Troy"
    GRAMME = 21, "Gramme"
    # Hectogramme (100 gms) = 22, "Hectogramme (100 gms)"
    KILOGRAMME = 23, "Kilogramme"
    # 100 kgs = 24, "100 kgs"
    # Tonne = 25, "Tonne"
    METRIC_CARAT = 26, "Metric Carat"
    # 50 kgs = 27, "50 kgs"
    MICROGRAM = 116, "Microgram"

    # 2. Gross weight
    # Pound gross = 60, "Pound gross"
    # Kilogramme gross = 61, "Kilogramme gross"
    # Quintal (100 kgs) gross = 62, "Quintal (100 kgs) gross"

    # 3. Unit
    NUMBER = 30, "Number"
    PAIR = 31, "Pair"
    # Dozen = 32, "Dozen"
    # Dozen Pair = 33, "Dozen Pair"
    # Hundred = 34, "Hundred"
    # Long Hundred = 35, "Long Hundred"
    # Gross = 36, "Gross"
    # Thousand = 37, "Thousand"
    # Short Standard = 38, "Short Standard"

    # 4. Area
    # Square inch = 41, "Square inch"
    # Square foot = 42, "Square foot"
    # Square yard = 43, "Square yard"
    # Square decimetre = 44, "Square decimetre"
    SQUARE_METRE = 45, "Square metre"
    # 100 square metres = 46, "100 square metres"

    # 5. Length
    # Inch = 50, "Inch"
    # Foot = 51, "Foot"
    # Yard = 52, "Yard"
    # 100 feet = 53, "100 feet"
    # Millimetre = 54, "Millimetre"
    # Centimetre = 55, "Centimetre"
    # Decimetre = 56, "Decimetre"
    # Metre = 57, "Metre"
    # Dekametre = 58, "Dekametre"
    # Hectometre = 59, "Hectometre"

    # 6. Capacity
    # Pint = 71, "Pint"
    # Gallon = 72, "Gallon"
    # 36 gallons (Bulk barrel) = 73, "36 gallons (Bulk barrel)"
    MILLILITRE_CU_CENTIMETRE = 74, "Millilitre (cu centimetre)"
    # Centilitre = 75, "Centilitre"
    LITRE = 76, "Litre"
    # Dekalitre = 77, "Dekalitre"
    # Hectolitre = 78, "Hectolitre"
    # US Gallon = 79, "US Gallon"
    # 1000 litre = 40, "1000 litre"

    # 7. Volume
    # Cubic inch = 81, "Cubic inch"
    # Cubic foot = 82, "Cubic foot"
    # Cubic yard = 83, "Cubic yard"
    # Standard = 84, "Standard"
    # Piled cubic fathom = 85, "Piled cubic fathom"
    # Cubic decimetre = 86, "Cubic decimetre"
    CUBIC_METRE = 87, "Cubic metre"
    # Piled cubic metre = 88, "Piled cubic metre"
    # Gram fissile isotopes = 89, "Gram fissile isotopes"

    # 8. Various
    # Kilogramme of H2O2 = 29, "Kilogramme of H2O2"
    # Kilogramme of K2O = 01, "Kilogramme of K2O"
    # Kilogramme of KOH = 02, "Kilogramme of KOH"
    # Kilogramme of N = 03, "Kilogramme of N"
    # Kilogramme of NaOH = 04, "Kilogramme of NaOH"
    # Kilogramme of P2O5 = 05, "Kilogramme of P2O5"
    # Kilogramme of U = 06, "Kilogramme of U"
    # Kilogramme of WO3 = 07, "Kilogramme of WO3"
    # Number of flasks = 08, "Number of flasks"
    # Number of kits = 09, "Number of kits"
    # Number of rolls = 10, "Number of rolls"
    # Number of sets = 19, "Number of sets"
    # 100 packs = 20, "100 packs"
    # 1000 tablets = 28, "1000 tablets"
    # 100 kilogram net dry matter = 48, "100 kilogram net dry matter"
    # 100 kilogram drained net weight = 49, "100 kilogram drained net weight"
    # Kilogram of choline chloride = 107, "Kilogram of choline chloride"
    # Kilogram of methyl amines = 39, "Kilogram of methyl amines"
    # Kilogramme of total alcohol = 63, "Kilogramme of total alcohol"
    # CCT carrying capacity in Tonnes (metric) shipping = 64, "CCT carrying capacity in Tonnes (metric) shipping"
    # Gram (fine gold content) = 65, "Gram (fine gold content)"
    # Litre of alcohol = 66, "Litre of alcohol"
    # Litre of alcohol in the spirit = 66, "Litre of alcohol in the spirit"
    # Litre of pure 100% alcohol = 66, "Litre of pure 100% alcohol"
    # Kilogramme 90% dry = 67, "Kilogramme 90% dry"
    # 90% tonne dry = 68, "90% tonne dry"
    # Kilogramme drained net weight = 69, "Kilogramme drained net weight"
    # Standard litre (of hydrocarbon oil) = 70, "Standard litre (of hydrocarbon oil)"
    # 1000 cubic metres = 80, "1000 cubic metres"
    # Curie = 90, "Curie"
    # Proof gallon = 91, "Proof gallon"
    # Displacement tonnage = 92, "Displacement tonnage"
    # Gross tonnage = 93, "Gross tonnage"
    # 100 international units = 94, "100 international units"
    # Million international units potency = 95, "Million international units potency"
    # Kilowatt = 96, "Kilowatt"
    # Kilowatt hour = 97, "Kilowatt hour"
    # Alcohol by Volume (ABV%) Beer = 98, "Alcohol by Volume (ABV%) Beer"
    # Degrees (Percentage Volume) = 99, "Degrees (Percentage Volume)"
    # TJ (gross calorific value) = 120, "TJ (gross calorific value)"
    # Euro per tonne of fuel = 112, "Euro per tonne of fuel"
    # Euro per tonne net of biodiesel content = 113, "Euro per tonne net of biodiesel content"
    # Kilometres = 114, "Kilometres"
    # Euro per tonne net of bioethanol content = 115, "Euro per tonne net of bioethanol content"
    # Number of watt = 117, "Number of watt"
    # Kilogram Raw Sugar = 118, "Kilogram Raw Sugar"
    # KAC: (KG net of Acesulfame Potassium) = 119, "KAC: (KG net of Acesulfame Potassium)"


class FakeChiefLicenceReplyEnum(TextChoices):
    ACCEPT = "accept", "Licences acceped by HMRC"
    REJECT = "reject", "Licences rejected by HMRC"
    FILE_ERROR = "file_error", "File has errors"
    UNKNOWN_ERROR = "unknown_error", "Unknown error as no response has been received from HMRC."

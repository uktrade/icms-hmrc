import re
import string

from rest_framework import serializers

from .enums import ControlledByEnum, LicenceActionEnum, LicenceTypeEnum, QuantityCodeEnum

ICMS_CASE_REF_PATTERN = re.compile(
    r"""
        ^       # Start of string
        [a-z]+  # Prefix
        /       # Separator
        \d+     # Year
        /       # Separator
        \d+     # reference
        (/\d+)? # Optional variation request
        $       # End of string
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

IMPORT_LICENCE_TYPES = [
    LicenceTypeEnum.IMPORT_DFL,
    LicenceTypeEnum.IMPORT_SIL,
    LicenceTypeEnum.IMPORT_OIL,
    LicenceTypeEnum.IMPORT_SAN,
]


class AddressSerializer(serializers.Serializer):
    line_1 = serializers.CharField(max_length=35)
    line_2 = serializers.CharField(required=False, max_length=35, allow_blank=True)
    line_3 = serializers.CharField(required=False, max_length=35, allow_blank=True)
    line_4 = serializers.CharField(required=False, max_length=35, allow_blank=True)
    line_5 = serializers.CharField(required=False, max_length=35, allow_blank=True)
    # TODO: Revisit in ECIL-486 part 2
    postcode = serializers.CharField(required=False, max_length=8, allow_blank=True)


class OrganisationSerializer(serializers.Serializer):
    # "GB" + 12 or 15 digits.
    eori_number = serializers.CharField(min_length=4, max_length=17)
    name = serializers.CharField(max_length=80, allow_blank=True)
    address = AddressSerializer()
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    def validate_eori_number(self, value: str) -> str:
        """Basic validation for EORI number.

        https://www.tax.service.gov.uk/check-eori-number
        """

        # This may need to be extended to include other prefixes (XI) in the future.
        if not value.upper().startswith("GB"):
            raise serializers.ValidationError("'eori_number' must start with 'GB' prefix")

        # Example value: GB123456789012345
        eori_number_length = len(value[2:])

        if eori_number_length != 12 and eori_number_length != 15:
            raise serializers.ValidationError(
                "'eori_number' must start with 'GB' followed by 12 or 15 numbers"
            )

        return value


class GoodSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=2000)

    def validate_description(self, value: str) -> str:
        _validate_description_whitespace(value)

        return value


class BaseSerializer(serializers.Serializer):
    """Baseclass serializer for all LicenceData records."""

    type = serializers.ChoiceField(choices=LicenceTypeEnum.choices)
    action = serializers.ChoiceField(choices=LicenceActionEnum.choices)

    # Unique UUID of this payload (as reference is not unique)
    id = serializers.UUIDField(format="hex_verbose")

    # The ICMS case reference (Unique per licenceData file - can be resent if updates fail)
    reference = serializers.RegexField(ICMS_CASE_REF_PATTERN, max_length=17)

    # The ICMS licence reference
    licence_reference = serializers.CharField(max_length=35)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class InsertAndReplacePayloadBase(BaseSerializer):
    """Base class for INSERT & REPLACE records"""

    action = serializers.ChoiceField([LicenceActionEnum.INSERT, LicenceActionEnum.REPLACE])

    organisation = OrganisationSerializer()
    restrictions = serializers.CharField(allow_blank=True, max_length=2000)
    goods = GoodSerializer(many=True, required=False, allow_null=True)

    # One of these must be supplied for all Firearm app types:
    country_group = serializers.CharField(max_length=4, required=False, allow_null=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_null=True)

    def validate(self, data) -> dict:
        data = super().validate(data)

        if not data.get("country_group") and not data.get("country_code"):
            raise serializers.ValidationError(
                "Either 'country_code' or 'country_group' should be set."
            )

        return data


class FirearmOilLicenceDataSerializer(InsertAndReplacePayloadBase):
    """FA-OIL licence data serializer"""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_OIL])


class FirearmDflLicenceDataSerializer(InsertAndReplacePayloadBase):
    """FA-DFL licence data serializer."""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_DFL])


class FirearmSilGoods(serializers.Serializer):
    # Required fields
    description = serializers.CharField(max_length=2000)
    controlled_by = serializers.ChoiceField(choices=ControlledByEnum.choices, required=True)

    # Conditional / Optional fields
    # Format in CHIEF SPEC: 9(11).9(3)
    quantity = serializers.DecimalField(
        decimal_places=3, max_digits=14, required=False, allow_null=True
    )
    unit = serializers.ChoiceField(
        choices=QuantityCodeEnum.choices, required=False, allow_null=True
    )

    def validate(self, data: dict[str, int | str]) -> dict[str, int | str]:
        data = super().validate(data)
        _validate_controlled_by(data)
        _validate_description_whitespace(data["description"])

        return data


class SanctionGoodsSerializer(serializers.Serializer):
    # Required fields
    commodity = serializers.CharField(max_length=11)
    controlled_by = serializers.ChoiceField(choices=ControlledByEnum.choices, required=True)

    # Conditional / Optional fields
    # Format in CHIEF SPEC: 9(11).9(3)
    quantity = serializers.DecimalField(
        decimal_places=3, max_digits=14, required=False, allow_null=True
    )
    unit = serializers.ChoiceField(
        choices=QuantityCodeEnum.choices, required=False, allow_null=True
    )

    def validate(self, data):
        data = super().validate(data)
        _validate_controlled_by(data)

        return data


class FirearmSilLicenceDataSerializer(InsertAndReplacePayloadBase):
    """FA-SIL licence data serializer."""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_SIL])
    goods = FirearmSilGoods(many=True)


class SanctionLicenceDataSerializer(InsertAndReplacePayloadBase):
    """Sanctions licence data serializer."""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_SAN])
    goods = SanctionGoodsSerializer(many=True)


class RevokeLicenceDataSerializer(BaseSerializer):
    """Revoke licence class used for CANCEL records."""

    action = serializers.ChoiceField([LicenceActionEnum.CANCEL])


def _validate_controlled_by(data: dict[str, int | str]) -> None:
    """Conditionally check that quantity / unit is set"""

    if data["controlled_by"] == ControlledByEnum.QUANTITY:
        if not data.get("quantity"):
            raise serializers.ValidationError(
                "'quantity' must be set when controlled_by equals 'Q'"
            )

        if not data.get("unit"):
            raise serializers.ValidationError("'unit' must be set when controlled_by equals 'Q'")


def _validate_description_whitespace(description: str) -> None:
    """Check for invalid whitespace characters in description"""
    whitespace = f'[{string.whitespace.replace(" ", "")}]'
    if re.search(whitespace, description) is not None:
        raise serializers.ValidationError("'description' contains an invalid whitespace character")

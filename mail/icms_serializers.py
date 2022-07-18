import re

from rest_framework import serializers

from .enums import ControlledByEnum, LicenceTypeEnum, QuantityCodeEnum

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
    postcode = serializers.CharField(max_length=8)


class OrganisationSerializer(serializers.Serializer):
    # TODO: ICMSLST-1658 Revisit turn / eori_number
    # turn = serializers.CharField(max_length=17)
    eori_number = serializers.CharField(max_length=17)
    name = serializers.CharField(max_length=80)
    address = AddressSerializer()
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


class GoodSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=2000)


class IcmsLicenceDataBaseSerializer(serializers.Serializer):
    """Baseclass serializer for all ICMS import applications."""

    type = serializers.ChoiceField(choices=IMPORT_LICENCE_TYPES)
    action = serializers.CharField()
    id = serializers.CharField()
    reference = serializers.CharField(max_length=35)
    case_reference = serializers.RegexField(ICMS_CASE_REF_PATTERN, max_length=17)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    organisation = OrganisationSerializer()
    restrictions = serializers.CharField(allow_blank=True, max_length=2000)
    goods = GoodSerializer(many=True, required=False, allow_null=True)

    # One of these must be supplied for all Firearm app types:
    country_group = serializers.CharField(max_length=4, required=False, allow_null=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_null=True)

    def validate(self, data) -> dict:
        data = super().validate(data)

        if not data.get("country_group") and not data.get("country_code"):
            raise serializers.ValidationError("Either 'country_code' or 'country_group' should be set.")

        return data


class FirearmOilLicenceDataSerializer(IcmsLicenceDataBaseSerializer):
    """FA-OIL licence data serializer"""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_OIL])


class FirearmDflLicenceDataSerializer(IcmsLicenceDataBaseSerializer):
    """FA-DFL licence data serializer."""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_DFL])


class FirearmSilGoods(serializers.Serializer):
    # Required fields
    description = serializers.CharField(max_length=2000)
    controlled_by = serializers.ChoiceField(choices=ControlledByEnum.choices, required=True)

    # Conditional / Optional fields
    # Format in CHIEF SPEC: 9(11).9(3)
    quantity = serializers.DecimalField(decimal_places=3, max_digits=14, required=False, allow_null=True)
    unit = serializers.ChoiceField(choices=QuantityCodeEnum.choices, required=False, allow_null=True)

    def validate(self, data):
        data = super().validate(data)
        _validate_controlled_by(data)

        return data


class SanctionGoodsSerializer(serializers.Serializer):
    # Required fields
    commodity = serializers.CharField(max_length=11)
    controlled_by = serializers.ChoiceField(choices=ControlledByEnum.choices, required=True)

    # Conditional / Optional fields
    # Format in CHIEF SPEC: 9(11).9(3)
    quantity = serializers.DecimalField(decimal_places=3, max_digits=14, required=False, allow_null=True)
    unit = serializers.ChoiceField(choices=QuantityCodeEnum.choices, required=False, allow_null=True)

    def validate(self, data):
        data = super().validate(data)
        _validate_controlled_by(data)

        return data


class FirearmSilLicenceDataSerializer(IcmsLicenceDataBaseSerializer):
    """FA-SIL licence data serializer."""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_SIL])
    goods = FirearmSilGoods(many=True)


class SanctionLicenceDataSerializer(IcmsLicenceDataBaseSerializer):
    """Sanctions licence data serializer."""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_SAN])
    goods = SanctionGoodsSerializer(many=True)


def _validate_controlled_by(data):
    """Conditionally check that quantity / unit is set"""

    if data["controlled_by"] == ControlledByEnum.QUANTITY:
        if not data.get("quantity"):
            raise serializers.ValidationError("'quantity' must be set when controlled_by equals 'Q'")

        if not data.get("unit"):
            raise serializers.ValidationError(f"'unit' must be set when controlled_by equals 'Q'")

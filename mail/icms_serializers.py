import re

from rest_framework import serializers

from .enums import LicenceTypeEnum

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

FIREARM_LICENCES = [LicenceTypeEnum.IMPORT_DFL, LicenceTypeEnum.IMPORT_SIL, LicenceTypeEnum.IMPORT_OIL]


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
    # Only enable these when we need them for other application types.
    # quantity = serializers.DecimalField(decimal_places=3, max_digits=13)
    # unit = serializers.ChoiceField(choices=enums.UnitMapping.serializer_choices())


class IcmsFaLicenceDataBaseSerializer(serializers.Serializer):
    """Baseclass serializer for all firearm applications"""

    type = serializers.ChoiceField(choices=FIREARM_LICENCES)
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


class FirearmOilLicenceDataSerializer(IcmsFaLicenceDataBaseSerializer):
    """FA-OIL licence data serializer"""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_OIL])


class FirearmDflLicenceDataSerializer(IcmsFaLicenceDataBaseSerializer):
    """FA-DFL licence data serializer."""

    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_DFL])


class FirearmSilGoods(GoodSerializer):
    controlled_by = serializers.ChoiceField(choices=["O", "Q"], required=True)
    quantity = serializers.DecimalField(decimal_places=3, max_digits=13, required=False, allow_null=True)

    def validate(self, data):
        """Conditionally check that quantity is set"""

        data = super().validate(data)

        if data["controlled_by"] == "Q" and not data.get("quantity"):
            raise serializers.ValidationError("'quantity' must be set when controlled_by equals 'Q'")

        return data


class FirearmSilLicenceDataSerializer(IcmsFaLicenceDataBaseSerializer):
    type = serializers.ChoiceField(choices=[LicenceTypeEnum.IMPORT_SIL])
    goods = FirearmSilGoods(many=True)

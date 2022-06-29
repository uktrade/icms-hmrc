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


class FaOilLicenceDataSerializer(IcmsFaLicenceDataBaseSerializer):
    """FA-OIL licence data serializer"""

    country_group = serializers.CharField(max_length=4)


class FaDflLicenceDataSerializer(IcmsFaLicenceDataBaseSerializer):
    """FA-DFL licence data serializer."""

    country_code = serializers.CharField(max_length=2)

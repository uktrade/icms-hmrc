import re

from rest_framework import serializers

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


class AddressSerializer(serializers.Serializer):
    line_1 = serializers.CharField(max_length=35)
    line_2 = serializers.CharField(required=False, max_length=35)
    line_3 = serializers.CharField(required=False, max_length=35)
    line_4 = serializers.CharField(required=False, max_length=35)
    line_5 = serializers.CharField(required=False, max_length=35)
    postcode = serializers.CharField(max_length=8)


class OrganisationSerializer(serializers.Serializer):
    # TODO: ICMSLST-1658 Revisit turn / eori_number
    # turn = serializers.CharField(max_length=12)
    eori_number = serializers.CharField(max_length=12)
    name = serializers.CharField(max_length=80)
    address = AddressSerializer()
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


class GoodSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=2000)
    # Only enable these when we need them for other application types.
    # quantity = serializers.DecimalField(decimal_places=3, max_digits=13)
    # unit = serializers.ChoiceField(choices=enums.UnitMapping.serializer_choices())


class IcmsFaOilLicenceDataSerializer(serializers.Serializer):
    """FA-OIL licence Data Serializer"""

    type = serializers.CharField()
    action = serializers.CharField()
    id = serializers.CharField()
    reference = serializers.CharField(max_length=35)
    case_reference = serializers.RegexField(ICMS_CASE_REF_PATTERN, max_length=17)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    organisation = OrganisationSerializer()
    country_group = serializers.CharField(required=False, allow_null=True, max_length=4)
    country_code = serializers.CharField(required=False, allow_null=True, max_length=2)
    restrictions = serializers.CharField(allow_blank=True, max_length=2000)
    goods = GoodSerializer(many=True, required=False, allow_null=True)

    def validate(self, data) -> dict:
        if not data.get("country_group") and not data.get("country_code"):
            raise serializers.ValidationError("Either 'country_code' or 'country_group' should be set.")

        return data

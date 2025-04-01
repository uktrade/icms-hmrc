import uuid

from parameterized import parameterized
from rest_framework.exceptions import ErrorDetail

from mail import serializers


class TestICMSLicenceDataSerializer:
    def test_invalid_case_reference(self):
        data = {"reference": "asdf/"}

        serializer = serializers.FirearmOilLicenceDataSerializer(data=data)
        assert not serializer.is_valid()

        expected_error = [
            ErrorDetail(string="This value does not match the required pattern.", code="invalid")
        ]
        assert serializer.errors["reference"] == expected_error

    def test_valid_case_reference(self):
        data = {"case_reference": "IMA/2022/00001"}
        serializer = serializers.FirearmOilLicenceDataSerializer(data=data)
        serializer.is_valid()

        assert "case_reference" not in serializer.errors

        data = {"case_reference": "IMA/2022/00001/99"}
        serializer = serializers.FirearmOilLicenceDataSerializer(data=data)
        serializer.is_valid()
        assert "case_reference" not in serializer.errors

    def test_invalid_goods_quantity(self):
        # test max decimal digits exceeded
        data = {"quantity": 123456789012}
        serializer = serializers.SanctionGoodsSerializer(data=data)
        assert not serializer.is_valid()

        expected_error = "Ensure that there are no more than 11 digits before the decimal point."
        assert serializer.errors["quantity"][0] == expected_error

        # test max decimal points exceeded
        data = {"quantity": 1234567890.1234}
        serializer = serializers.SanctionGoodsSerializer(data=data)
        assert not serializer.is_valid()

        expected_error = "Ensure that there are no more than 3 decimal places."
        assert serializer.errors["quantity"][0] == expected_error

        # Test max digits exceeded
        data = {"quantity": 123456789012.123}
        serializer = serializers.SanctionGoodsSerializer(data=data)
        assert not serializer.is_valid()

        expected_error = "Ensure that there are no more than 14 digits in total."
        assert serializer.errors["quantity"][0] == expected_error

    def test_valid_goods_quantity(self):
        data = {"quantity": 12345678901.123}
        serializer = serializers.FirearmOilLicenceDataSerializer(data=data)
        serializer.is_valid()

        assert "quantity" not in serializer.errors

    def test_valid_fa_oil_payload(self, fa_oil_insert_payload):
        data = fa_oil_insert_payload
        serializer = serializers.FirearmOilLicenceDataSerializer(data=data)

        is_valid = serializer.is_valid()

        assert is_valid

        # Check all the keys here are in the validated data
        for key in data.keys():
            assert key in serializer.validated_data

    def test_valid_fa_oil_payload_empty_postcode(self, fa_oil_insert_payload):
        data = fa_oil_insert_payload
        data["organisation"]["address"]["postcode"] = ""

        serializer = serializers.FirearmOilLicenceDataSerializer(data=data)

        is_valid = serializer.is_valid()

        assert is_valid

        # Check all the keys here are in the validated data
        for key in data.keys():
            assert key in serializer.validated_data

    def test_at_least_one_country_field_is_set(self):
        data = {
            "type": "OIL",
            "action": "insert",
            "id": "deaa301d-d978-473b-b76b-da275f28f447",
            "reference": "IMA/2022/00001",
            "licence_reference": "GBOIL2222222C",
            "start_date": "2022-06-06",
            "end_date": "2025-05-30",
            "organisation": {
                "eori_number": "GB112233445566000",
                "name": "org name",
                "address": {
                    "line_1": "line_1",
                    "line_2": "line_2",
                    "line_3": "line_3",
                    "line_4": "line_4",
                    "line_5": "line_5",
                    "postcode": "S118ZZ",  # /PS-IGNORE
                },
            },
            "restrictions": "Some restrictions.\nSome more restrictions",
            "goods": [
                {
                    "description": (
                        "Firearms, component parts thereof, or ammunition of"
                        " any applicable commodity code, other than those"
                        " falling under Section 5 of the Firearms Act 1968"
                        " as amended."
                    ),
                }
            ],
        }

        serializer = serializers.FirearmOilLicenceDataSerializer(data=data)

        assert not serializer.is_valid()

        expected_error = [
            ErrorDetail(
                string="Either 'country_code' or 'country_group' should be set.", code="invalid"
            )
        ]

        assert serializer.errors["non_field_errors"] == expected_error

    def test_valid_fa_dfl_payload(self):
        data = {
            "type": "DFL",
            "action": "insert",
            "id": str(uuid.uuid4()),
            "reference": "IMA/2022/00001",
            "licence_reference": "GBSIL1111111C",
            "start_date": "2022-06-06",
            "end_date": "2025-05-30",
            "organisation": {
                "eori_number": "GB112233445566000",
                "name": "org name",
                "address": {
                    "line_1": "line_1",
                    "line_2": "line_2",
                    "line_3": "line_3",
                    "line_4": "line_4",
                    "line_5": "line_5",
                    "postcode": "S118ZZ",  # /PS-IGNORE
                    "start_date": None,
                    "end_date": None,
                },
            },
            "country_code": "AU",
            "restrictions": "Some restrictions.\nSome more restrictions",
            "goods": [
                {
                    "description": (
                        "Firearms, component parts thereof, or ammunition of"
                        " any applicable commodity code, other than those"
                        " falling under Section 5 of the Firearms Act 1968"
                        " as amended."
                    ),
                }
            ],
        }

        serializer = serializers.FirearmDflLicenceDataSerializer(data=data)

        is_valid = serializer.is_valid()

        assert is_valid

        # Check all the keys here are in the validated data
        for key in data.keys():
            assert key in serializer.validated_data

    def test_invalid_dfl_newline_error(self, fa_dfl_insert_payload):
        data = fa_dfl_insert_payload
        data["goods"] = [{"description": "goods\ndescription"}]
        serializer = serializers.FirearmDflLicenceDataSerializer(data=data)

        assert not serializer.is_valid()

        expected_error = [
            ErrorDetail(
                string="'description' contains an invalid whitespace character", code="invalid"
            )
        ]
        goods_error = serializer.errors["goods"][0]["description"]
        assert goods_error == expected_error

    def test_valid_fa_sil_payload(self, fa_sil_insert_payload):
        data = fa_sil_insert_payload
        serializer = serializers.FirearmSilLicenceDataSerializer(data=data)
        is_valid = serializer.is_valid()

        assert is_valid

        # Check all the keys here are in the validated data
        for key in data.keys():
            assert key in serializer.validated_data

    def test_controlled_by_and_quantity_errors(self, fa_sil_insert_payload):
        data = fa_sil_insert_payload
        data["goods"] = [
            {"controlled_by": "Q", "description": "goods description", "unit": 30},
        ]
        serializer = serializers.FirearmSilLicenceDataSerializer(data=data)

        assert not serializer.is_valid()

        expected_error = [
            ErrorDetail(
                string="'quantity' must be set when controlled_by equals 'Q'", code="invalid"
            )
        ]
        goods_error = serializer.errors["goods"][0]["non_field_errors"]
        assert goods_error == expected_error

    def test_controlled_by_and_unit_errors(self, fa_sil_insert_payload):
        data = fa_sil_insert_payload
        data["goods"] = [
            {"controlled_by": "Q", "description": "goods description", "quantity": 30},
        ]
        serializer = serializers.FirearmSilLicenceDataSerializer(data=data)

        assert not serializer.is_valid()

        expected_error = [
            ErrorDetail(string="'unit' must be set when controlled_by equals 'Q'", code="invalid")
        ]
        goods_error = serializer.errors["goods"][0]["non_field_errors"]
        assert goods_error == expected_error

    def test_sil_invalid_description_carriage_return_error(self, fa_sil_insert_payload):
        data = fa_sil_insert_payload
        data["goods"] = [
            {
                "controlled_by": "Q",
                "description": "goods\r\ndescription",
                "quantity": 30,
                "unit": 30,
            },
        ]
        serializer = serializers.FirearmSilLicenceDataSerializer(data=data)

        assert not serializer.is_valid()

        expected_error = [
            ErrorDetail(
                string="'description' contains an invalid whitespace character", code="invalid"
            )
        ]
        goods_error = serializer.errors["goods"][0]["non_field_errors"]
        assert goods_error == expected_error

    def test_sil_invalid_description_tab_error(self, fa_sil_insert_payload):
        data = fa_sil_insert_payload
        data["goods"] = [
            {"controlled_by": "Q", "description": "goods\tdescription", "quantity": 30, "unit": 30},
        ]
        serializer = serializers.FirearmSilLicenceDataSerializer(data=data)

        assert not serializer.is_valid()

        expected_error = [
            ErrorDetail(
                string="'description' contains an invalid whitespace character", code="invalid"
            )
        ]
        goods_error = serializer.errors["goods"][0]["non_field_errors"]
        assert goods_error == expected_error

    def test_valid_sanction_payload(self, sanctions_insert_payload):
        data = sanctions_insert_payload
        serializer = serializers.SanctionLicenceDataSerializer(data=data)
        is_valid = serializer.is_valid()

        assert is_valid

        # Check all the keys here are in the validated data
        for key in data.keys():
            assert key in serializer.validated_data

    def test_valid_nuclear_material_payload(self, nuclear_insert_payload):
        data = nuclear_insert_payload

        serializer = serializers.NuclearMaterialLicenceDataSerializer(data=data)
        is_valid = serializer.is_valid()

        assert is_valid

        # Check all the keys here are in the validated data
        for key in data.keys():
            assert key in serializer.validated_data

    @parameterized.expand(
        [
            ("Prefix missing", "00000000000000", "'eori_number' must start with 'GB' prefix"),
            ("EORI too short", "GBP", "Ensure this field has at least 4 characters."),
            (
                "EORI too long",
                "GB00000000000000000",
                "Ensure this field has no more than 17 characters.",
            ),
            (
                "EORI length not 12 or 15",
                "GB0000000000000",
                "'eori_number' must start with 'GB' followed by 12 or 15 numbers",
            ),
        ]
    )
    def test_eori_number_errors(self, name, eori, expected_error):
        data = {"eori_number": eori}

        serializer = serializers.OrganisationSerializer(data=data)
        assert not serializer.is_valid()

        assert str(serializer.errors["eori_number"][0]) == expected_error, f"{name} test failed"

    def test_eori_number_gbpr(self):
        data = {
            "eori_number": "GB123451234512345",
            "name": "org name",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "line_4",
                "line_5": "line_5",
                "postcode": "S118ZZ",  # /PS-IGNORE
            },
        }
        serializer = serializers.OrganisationSerializer(data=data)
        assert serializer.is_valid()

    def test_valid_fa_sil_revoke_payload(self, fa_sil_revoke_payload):
        data = fa_sil_revoke_payload
        serializer = serializers.RevokeLicenceDataSerializer(data=data)
        is_valid = serializer.is_valid()

        assert is_valid

        # Check all the keys here are in the validated data
        for key in data.keys():
            assert key in serializer.validated_data

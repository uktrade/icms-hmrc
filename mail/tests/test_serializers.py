import uuid

from django.test import TestCase, override_settings
from rest_framework.exceptions import ErrorDetail

from mail import icms_serializers
from mail.enums import ChiefSystemEnum, LicenceTypeEnum, UnitMapping
from mail.serializers import LiteLicenceDataSerializer


class LiteLicenceDataSerializerTestCase(TestCase):
    def test_no_data(self):
        serializer = LiteLicenceDataSerializer(data={})

        self.assertFalse(serializer.is_valid())
        expected_errors = {
            "action": ["This field is required."],
            "end_date": ["This field is required."],
            "id": ["This field is required."],
            "reference": ["This field is required."],
            "start_date": ["This field is required."],
            "type": ["This field is required."],
        }
        self.assertDictEqual(serializer.errors, expected_errors)

    def test_old_id_required_when_action_is_update(self):
        data = {
            "action": "update",
            "end_date": "1999-12-31",
            "id": "foo",
            "reference": "bar",
            "start_date": "1999-12-31",
            "type": "baz",
        }
        serializer = LiteLicenceDataSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        expected_errors = {
            "old_id": ["This field is required."],
        }
        self.assertDictEqual(serializer.errors, expected_errors)

    def test_invalid_old_id_when_action_is_update(self):
        data = {
            "action": "update",
            "end_date": "1999-12-31",
            "id": "foo",
            # This is a valid UUID-format key, but there is no matching
            # record in the database.
            "old_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "reference": "bar",
            "start_date": "1999-12-31",
            "type": "baz",
        }
        serializer = LiteLicenceDataSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        expected_errors = {
            "old_id": ["This licence does not exist in HMRC integration records"],
        }
        self.assertDictEqual(serializer.errors, expected_errors)

    def test_required_fields_for_open_or_general_type(self):
        for type_ in LicenceTypeEnum.OPEN_LICENCES + LicenceTypeEnum.OPEN_GENERAL_LICENCES:
            with self.subTest(type_=type_):
                data = {
                    "action": "insert",
                    "end_date": "1999-12-31",
                    "id": "foo",
                    "reference": "bar",
                    "start_date": "1999-12-31",
                    "type": type_,
                }
                serializer = LiteLicenceDataSerializer(data=data)

                self.assertFalse(serializer.is_valid())

                expected_errors = {
                    "countries": ["This field is required."],
                }
                self.assertDictEqual(serializer.errors, expected_errors)

    def test_required_fields_for_standard_type(self):
        for type_ in LicenceTypeEnum.STANDARD_LICENCES:
            with self.subTest(type_=type_):
                data = {
                    "action": "insert",
                    "end_date": "1999-12-31",
                    "id": "foo",
                    "reference": "bar",
                    "start_date": "1999-12-31",
                    "type": type_,
                }
                serializer = LiteLicenceDataSerializer(data=data)

                self.assertFalse(serializer.is_valid())

                expected_errors = {
                    "end_user": ["This field is required."],
                    "goods": ["This field is required."],
                }
                self.assertDictEqual(serializer.errors, expected_errors)

    def test_minimum_countries_for_open_type(self):
        # For open licence types, the request data must include at least 1
        # country item.
        data = {
            "action": "insert",
            "end_date": "1999-12-31",
            "id": "foo",
            "reference": "bar",
            "start_date": "1999-12-31",
            "type": LicenceTypeEnum.OPEN_LICENCES[0],
            "countries": [],
        }
        serializer = LiteLicenceDataSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        expected_errors = {
            "countries": {
                "non_field_errors": ["Ensure this field has at least 1 elements."],
            },
        }
        self.assertDictEqual(serializer.errors, expected_errors)

    def test_valid_countries_for_open_type(self):
        data = {
            "action": "insert",
            "end_date": "1999-12-31",
            "id": "foo",
            "reference": "bar",
            "start_date": "1999-12-31",
            "type": LicenceTypeEnum.OPEN_LICENCES[0],
            "countries": [
                {
                    "id": "GB",
                    "name": "United Kingdom",
                }
            ],
        }
        serializer = LiteLicenceDataSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_goods_invalid_choice_for_unit(self):
        data = {
            "action": "insert",
            "end_date": "1999-12-31",
            "id": "foo",
            "reference": "bar",
            "start_date": "1999-12-31",
            "type": "siel",  # Standard type, which requires "goods".
            "end_user": {
                "name": "Foo",
                "address": {
                    "line_1": "Line1",
                    "country": {"id": "GB", "name": "GB"},
                },
            },
            # This "goods" nested object is what we are testing.
            "goods": [
                {
                    "description": "",
                    "name": "Bar",
                    "quantity": "1",
                    "unit": "XyzUnit",
                },
            ],
        }
        serializer = LiteLicenceDataSerializer(data=data)
        serializer.is_valid()

        expected_errors = {
            "goods": [
                {"unit": ['"XyzUnit" is not a valid choice.']},
            ],
        }
        self.assertDictEqual(serializer.errors, expected_errors)

    def test_goods_valid_choice_for_unit(self):
        data = {
            "action": "insert",
            "end_date": "1999-12-31",
            "id": "foo",
            "reference": "bar",
            "start_date": "1999-12-31",
            "type": "siel",  # Standard type, which requires "goods".
            "end_user": {
                "name": "Foo",
                "address": {
                    "line_1": "Line1",
                    "country": {"id": "GB", "name": "GB"},
                },
            },
            # This "goods" nested object is what we are testing.
            "goods": [
                {
                    "description": "",
                    "name": "Bar",
                    "quantity": "1",
                    "unit": "XyzUnit",
                },
            ],
        }

        for unit_label in UnitMapping.__members__:
            # `unit_label` is each of the strings, like "NAR", "ITG", etc.
            with self.subTest(unit=unit_label):
                data["goods"][0]["unit"] = unit_label
                serializer = LiteLicenceDataSerializer(data=data)
                is_valid = serializer.is_valid()

                self.assertDictEqual(serializer.errors, {})
                self.assertTrue(is_valid)


@override_settings(CHIEF_SOURCE_SYSTEM=ChiefSystemEnum.ICMS)
class ICMSLicenceDataSerializerTestCase(TestCase):
    def test_invalid_case_reference(self):
        data = {"case_reference": "asdf/"}

        serializer = icms_serializers.FirearmOilLicenceDataSerializer(data=data)

        self.assertFalse(serializer.is_valid())

        expected_error = [ErrorDetail(string="This value does not match the required pattern.", code="invalid")]
        self.assertEqual(serializer.errors["case_reference"], expected_error)

    def test_valid_case_reference(self):
        data = {"case_reference": "IMA/2022/00001"}
        serializer = icms_serializers.FirearmOilLicenceDataSerializer(data=data)
        serializer.is_valid()
        self.assertNotIn("case_reference", serializer.errors)

        data = {"case_reference": "IMA/2022/00001/99"}
        serializer = icms_serializers.FirearmOilLicenceDataSerializer(data=data)
        serializer.is_valid()
        self.assertNotIn("case_reference", serializer.errors)

    def test_valid_fa_oil_payload(self):
        data = {
            "type": "OIL",
            "action": "insert",
            "id": str(uuid.uuid4()),
            "reference": "GBOIL2222222C",
            "case_reference": "IMA/2022/00001",
            "start_date": "2022-06-06",
            "end_date": "2025-05-30",
            "organisation": {
                "eori_number": "112233445566",
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
            "country_group": "G001",
            "restrictions": "Some restrictions.\n\n Some more restrictions",
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

        serializer = icms_serializers.FirearmOilLicenceDataSerializer(data=data)

        is_valid = serializer.is_valid()

        self.assertTrue(is_valid)

        # Check all the keys here are in the validated data
        for key in data.keys():
            self.assertIn(key, serializer.validated_data)

    def test_at_least_one_country_field_is_set(self):
        data = {
            "type": "OIL",
            "action": "insert",
            "id": str(uuid.uuid4()),
            "reference": "GBOIL2222222C",
            "case_reference": "IMA/2022/00001",
            "start_date": "2022-06-06",
            "end_date": "2025-05-30",
            "organisation": {
                "eori_number": "112233445566",
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
            "restrictions": "Some restrictions.\n\n Some more restrictions",
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

        serializer = icms_serializers.FirearmOilLicenceDataSerializer(data=data)

        self.assertFalse(serializer.is_valid())

        expected_error = [ErrorDetail(string="Either 'country_code' or 'country_group' should be set.", code="invalid")]
        self.assertEqual(serializer.errors["non_field_errors"], expected_error)

    def test_valid_fa_dfl_payload(self):
        data = {
            "type": "DFL",
            "action": "insert",
            "id": str(uuid.uuid4()),
            "reference": "GBOIL2222222C",
            "case_reference": "IMA/2022/00001",
            "start_date": "2022-06-06",
            "end_date": "2025-05-30",
            "organisation": {
                "eori_number": "112233445566",
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
            "restrictions": "Some restrictions.\n\n Some more restrictions",
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

        serializer = icms_serializers.FirearmDflLicenceDataSerializer(data=data)

        is_valid = serializer.is_valid()

        self.assertTrue(is_valid)

        # Check all the keys here are in the validated data
        for key in data.keys():
            self.assertIn(key, serializer.validated_data)

    def test_valid_fa_sil_payload(self):
        data = get_valid_fa_sil_payload()
        serializer = icms_serializers.FirearmSilLicenceDataSerializer(data=data)
        is_valid = serializer.is_valid()

        self.assertTrue(is_valid)

        # Check all the keys here are in the validated data
        for key in data.keys():
            self.assertIn(key, serializer.validated_data)

    def test_controlled_by_and_quantity_errors(self):
        data = get_valid_fa_sil_payload()
        data["goods"] = [
            {"controlled_by": "Q", "description": "goods description"},
        ]
        serializer = icms_serializers.FirearmSilLicenceDataSerializer(data=data)

        self.assertFalse(serializer.is_valid())

        expected_error = [ErrorDetail(string="'quantity' must be set when controlled_by equals 'Q'", code="invalid")]
        goods_error = serializer.errors["goods"][0]["non_field_errors"]
        self.assertEqual(goods_error, expected_error)


def get_valid_fa_sil_payload():
    goods = [
        {"description": "Sample goods description 1", "quantity": 1, "controlled_by": "Q"},
        {"description": "Sample goods description 2", "quantity": 2, "controlled_by": "Q"},
        {"description": "Sample goods description 3", "quantity": 3, "controlled_by": "Q"},
        {"description": "Sample goods description 4", "quantity": 4, "controlled_by": "Q"},
        {"description": "Sample goods description 5", "quantity": 5, "controlled_by": "Q"},
        {"description": "Unlimited Description goods line", "controlled_by": "O"},
    ]

    return {
        "type": "SIL",
        "action": "insert",
        "id": str(uuid.uuid4()),
        "reference": "GBSIL3333333H",
        "case_reference": "IMA/2022/00003",
        "start_date": "2022-06-29",
        "end_date": "2024-12-29",
        "organisation": {
            "eori_number": "123456654321",
            "name": "SIL Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "",
                "line_5": "",
                "postcode": "S227ZZ",
            },
        },
        "country_code": "US",
        "restrictions": "Sample restrictions",
        "goods": goods,
    }

from django.test import TestCase

from mail.enums import LicenceTypeEnum, UnitMapping
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

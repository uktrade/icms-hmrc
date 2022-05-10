import unittest

from mail.enums import UnitMapping


class UnitMappingTests(unittest.TestCase):
    def test_convert_code(self):
        data = [
            ("NAR", 30),
            ("GRM", 21),
            ("KGM", 23),
            ("MTK", 45),
            ("MTR", 57),
            ("LTR", 94),
            ("MTQ", 2),
            ("ITG", 30),
        ]

        for code, value in data:
            with self.subTest(code=code, value=value):
                self.assertEqual(value, UnitMapping.convert(code))

    def test_convert_none(self):
        self.assertIsNone(UnitMapping.convert(None))

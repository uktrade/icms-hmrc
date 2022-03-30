import unittest

from parameterized import parameterized

from mail.libraries import edifact_validator


class LicenceToEdifactValidationTests(unittest.TestCase):
    @parameterized.expand(
        [
            ("1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\202104090304\\96839\\Y", 0),
            ("1\\fileHeader\\SPIRE\\SPIRE\\licenceData\\202104090304\\96839\\Y", 1),
            ("1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\202104090304\\96839", 1),
            ("1\\fileHeaders\\SPIRE\\CHIEF\\licenceUpdate\\202104090304\\96839\\Y", 2),
            ("1\\fileHeader\\SPIRE\\CHIEF\\licenceUpdate\\202104090304\\96839\\T", 2),
        ]
    )
    def test_file_header_validation(self, header, num_errors):
        errors = edifact_validator.validate_file_header(header)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("2\\licence\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIE\\E\\20210408\\20220408", 0),
            ("2\\licences\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIE\\E\\20210408\\20220408", 1),
            ("2\\licences\\20210000006TA\\add\\GBSIEL/2021/0000006/T/A\\SIE\\E\\20210408\\20220408", 2),
            ("2\\licence\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIEL\\E\\20210408\\20220408", 1),
            ("2\\licence\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIEL\\T\\20210408\\20220408", 2),
        ]
    )
    def test_licence_transaction_header_validation(self, licence_tx_line, num_errors):
        errors = edifact_validator.validate_licence_transaction_header("licenceData", licence_tx_line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            (
                "3\\trader\\\\GB123456789000\\20210408\\20220408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                0,
            ),
            (
                "3\\traders\\\\GB123456789000\\20210408\\20220408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                1,
            ),
            (
                "3\\trader\\\\\\20210408\\20220408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                2,
            ),
            (
                "3\\trader\\\\\\20210408\\20200408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                3,
            ),
            (
                "3\\trader\\\\GB123456789000\\20210408\\20200408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\Islington",
                2,
            ),
            (
                "3\\trader\\\\GB123456789000\\20210408\\20220408\\Very long organisation name to trigger validation error, max length is 80 characters\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                1,
            ),
            (
                "3\\trader\\\\6\\20210408\\20220408\\Very long organisation name to trigger validation error, max length is 80 characters\\This is a very long address line to trigger error\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                3,
            ),
            (
                "3\\trader\\\\GB123456789000\\20210408\\20220408\\Very long organisation name to trigger validation error, max length is 80 characters\\This is a very long address line to trigger error\\windsor house\\\\Windsor\\Surrey\\INVALID POSTCODE",
                3,
            ),
        ]
    )
    def test_permitted_trader_validation(self, line, num_errors):
        errors = edifact_validator.validate_permitted_trader(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("4\\country\\AU\\\\D", 0),
            ("4\\country\\AU\\", 1),
            ("4\\country\\AU\\\\T", 1),
            ("4\\country_id\\AU\\AU\\D", 2),
        ]
    )
    def test_country_validation(self, line, num_errors):
        errors = edifact_validator.validate_country(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("5\\foreignTrader\\Test party\\1234\\\\\\\\\\\\AU", 0),
            ("5\\foreignTrader\\Test party\\1234\\\\\\\\\\", 1),
            ("5\\foreignTraders\\Test party\\1234\\\\\\\\\\\\AU", 1),
            (
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Very long\\address line_2 exceeding 35 chars\\Very long address line_3 exceeding\\35 chars Queensland NSW 42551\\\\\\GB",
                0,
            ),
            (
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Very long\\address line_2 exceeding 35 chars\\Very long address line_3 exceeding\\35 chars Queensland NSW 42551 make it longer\\\\\\GB",
                1,
            ),
            (
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Very long\\address line_2 exceeding 35 chars\\Very long address line_3 exceeding\\35 chars Queensland NSW 42551\\\\123456789\\GBR",
                2,
            ),
        ]
    )
    def test_foreign_trader_validation(self, line, num_errors):
        errors = edifact_validator.validate_foreign_trader(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("6\\restrictions\\Provisos may apply please see licence", 0),
            ("6\\restrictions", 1),
            ("6\\restrictionsline\\Provisos may apply please see licence", 1),
        ]
    )
    def test_restrictions_validation(self, line, num_errors):
        errors = edifact_validator.validate_restrictions(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("7\\line\\1\\\\\\\\\\Rifle\\Q\\\\030\\\\4\\\\\\\\\\\\", 0),
            ("7\\line\\1\\\\\\\\\\Rifle\\Q\\\\030\\\\\\\\\\\\\\", 1),
            ("7\\lines\\1\\\\\\\\\\Rifle\\Q\\\\030\\\\4\\\\\\\\\\\\", 1),
            ("7\\line\\1\\\\\\\\\\Rifle\\T\\\\30\\\\4\\\\\\\\\\\\", 2),
            ("7\\lines\\1\\\\\\\\\\\\Q\\\\030\\\\4\\\\\\\\\\\\", 2),
        ]
    )
    def test_licence_product_line_validation(self, line, num_errors):
        errors = edifact_validator.validate_licence_product_line(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("10\\end\\licence\\9", 0),
            ("10\\end\\licence", 1),
            ("10\\ending\\licence\\9", 1),
        ]
    )
    def test_end_line_validation(self, line, num_errors):
        errors = edifact_validator.validate_end_line(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("11\\fileTrailer\\1", 0),
            ("11\\fileTrailer", 1),
            ("11\\fileTrailers\\1", 1),
        ]
    )
    def test_file_trailer_validation(self, line, num_errors):
        errors = edifact_validator.validate_file_trailer(line)
        self.assertEqual(len(errors), num_errors)

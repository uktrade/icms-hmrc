import typing
import unittest

from mail.libraries import chiefprotocol
from mail.libraries.chieftypes import End, FileHeader, FileTrailer, Licence, LicenceDataLine, _Record


class ResolveLineNumbersTest(unittest.TestCase):
    def test_add_line_numbers(self):
        lines = [
            FileHeader(),
            FileTrailer(),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        # Easy: just add numbers in order, starting at 1.
        expected = [
            FileHeader(lineno=1),
            FileTrailer(lineno=2),
        ]
        self.assertEqual(result, expected)

    def test_end_transaction_1(self):
        lines = [
            Licence(),
            End(start_record_type=Licence.type_),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        # An "end" line references a previous type of line, and we append
        # the number of lines between the start/end (inclusive).
        expected = [
            Licence(lineno=1, type_="licence"),
            End(lineno=2, start_record_type="licence", record_count=2),
        ]
        self.assertEqual(result, expected)

    def test_end_transaction_2(self):
        lines = [
            Licence(),
            LicenceDataLine(),
            LicenceDataLine(),
            End(start_record_type=Licence.type_),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        # There can be multiple lines between the start and "end" lines.
        expected_last_line = End(lineno=4, start_record_type="licence", record_count=4)
        self.assertEqual(result[-1], expected_last_line)

    def test_nested_end_transactions(self):
        lines = [
            FileHeader(),
            Licence(),
            LicenceDataLine(),
            End(start_record_type=Licence.type_),
            Licence(),
            LicenceDataLine(),
            End(start_record_type=Licence.type_),
            FileTrailer(),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        expected = [
            FileHeader(lineno=1),
            Licence(lineno=2),
            LicenceDataLine(lineno=3),
            End(lineno=4, start_record_type="licence", record_count=3),
            Licence(lineno=5),
            LicenceDataLine(lineno=6),
            End(lineno=7, start_record_type="licence", record_count=3),
            FileTrailer(lineno=8),
        ]
        self.assertEqual(result, expected)


class FormatLineTest(unittest.TestCase):
    def test_format_stringy_type(self):
        class Stringy:
            def __str__(self):
                return "qux!"

        line = _Record(lineno=None, type_=Stringy())
        result = chiefprotocol.format_line(line)

        self.assertEqual(result, "\\qux!")

    def test_format_none_type(self):
        line = _Record(lineno=None, type_=None)
        result = chiefprotocol.format_line(line)

        # `None` was formatted as the empty string.
        self.assertEqual(result, "\\")


class FormatLinesTest(unittest.TestCase):
    def test_format_lines(self):
        lines = [
            FileHeader(),
            Licence(),
            End(start_record_type=Licence.type_),
        ]
        result = chiefprotocol.format_lines(lines)

        expected = "1\\fileHeader\\\\\\\\\\\\\n" "2\\licence\\\\\\\\\\\\\\\n" "3\\end\\licence\\2\n"
        self.assertEqual(result, expected)


class CountTransactionsTest(unittest.TestCase):
    def test_count_zero_licences(self):
        lines = [
            FileHeader(),
            FileTrailer(),
        ]
        result = chiefprotocol.count_transactions(lines)

        self.assertEqual(result, 0)

    def test_count_many_licences(self):
        lines = [
            FileHeader(),
            Licence(),
            End(start_record_type=Licence.type_),
            Licence(),
            End(start_record_type=Licence.type_),
            FileTrailer(),
        ]
        result = chiefprotocol.count_transactions(lines)

        self.assertEqual(result, 2)

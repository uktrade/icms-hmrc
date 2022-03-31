import unittest

from mail.libraries import chiefprotocol


class ResolveLineNumbersTest(unittest.TestCase):
    def test_add_line_numbers(self):
        lines = [
            ("foo",),
            ("bar",),
            ("baz",),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        # Easy: just add numbers in order, starting at 1.
        expected = [
            (1, "foo"),
            (2, "bar"),
            (3, "baz"),
        ]
        self.assertEqual(result, expected)

    def test_end_transaction_1(self):
        lines = [
            ("foo",),
            ("end", "foo"),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        # An "end" line references a previous type of line, and we append
        # the number of lines between the start/end (inclusive).
        expected = [
            (1, "foo"),
            (2, "end", "foo", 2),
        ]
        self.assertEqual(result, expected)

    def test_end_transaction_2(self):
        lines = [
            ("foo",),
            ("bar",),
            ("baz",),
            ("end", "foo"),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        # There can be multiple lines between the start and "end" lines.
        expected = [
            (1, "foo"),
            (2, "bar"),
            (3, "baz"),
            (4, "end", "foo", 4),
        ]
        self.assertEqual(result, expected)

    def test_nested_end_transactions(self):
        lines = [
            ("foo",),
            ("bar",),
            ("baz",),
            ("end", "bar"),
            ("bar",),
            ("baz",),
            ("end", "bar"),
            ("end", "foo"),
        ]
        result = chiefprotocol.resolve_line_numbers(lines)

        # We have 2 "end" types of "bar".
        expected = [
            (1, "foo"),
            (2, "bar"),
            (3, "baz"),
            (4, "end", "bar", 3),
            (5, "bar"),
            (6, "baz"),
            (7, "end", "bar", 3),
            (8, "end", "foo", 8),
        ]
        self.assertEqual(result, expected)


class FormatLineTest(unittest.TestCase):
    def test_format_stringy_type(self):
        class Stringy:
            def __str__(self):
                return "qux!"

        line = ("foo", Stringy(), "bar")
        result = chiefprotocol.format_line(line)

        self.assertEqual(result, "foo\\qux!\\bar")

    def test_format_none_type(self):
        line = ("foo", None, "bar")
        result = chiefprotocol.format_line(line)

        # `None` was formatted as the empty string.
        self.assertEqual(result, "foo\\\\bar")


class FormatLinesTest(unittest.TestCase):
    def test_format_lines(self):
        lines = [
            ("fileHeader",),
            ("licence",),
            ("end", "licence"),
        ]
        result = chiefprotocol.format_lines(lines)

        expected = "1\\fileHeader\n2\\licence\n3\\end\\licence\\2\n"
        self.assertEqual(result, expected)


class CountTransactionsTest(unittest.TestCase):
    def test_count_zero_licences(self):
        lines = [
            ("fileHeader",),
            ("fileTrailer",),
        ]
        result = chiefprotocol.count_transactions(lines)

        self.assertEqual(result, 0)

    def test_count_many_licences(self):
        lines = [
            ("fileHeader",),
            ("licence",),
            ("end", "licence"),
            ("licence",),
            ("end", "licence"),
            ("fileTrailer",),
        ]
        result = chiefprotocol.count_transactions(lines)

        self.assertEqual(result, 2)

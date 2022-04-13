# The CHIEF message protocol(s). "TIS" means technical interface specification.
# DES235: TIS LINE FILE DIALOGUE AND SYNTAX
# DES236: TIS – Licence Maintenance and Usage
#
# TIS spec jargon:
# - M: mandatory (required)
# - O: optional
# - C: conditional
# - A: absent (must not be present)


import dataclasses
import typing

from . import chieftypes

FIELD_SEP = "\\"  # A single back-slash character.
LINE_SEP = "\n"


def resolve_line_numbers(lines: typing.Sequence[chieftypes._Record]) -> list:
    """Add line numbers for a CHIEF message.

    For "end" lines, we keep track of the number of lines since the matching
    opening line type, and add that number to the end of the line.
    """
    starts = {}
    result = []

    for lineno, line in enumerate(lines, start=1):
        # Track the most recent line number for each line type.
        starts[line.type_] = lineno
        line.lineno = lineno

        if line.type_ == chieftypes.End.type_:
            # End lines are like ("end", <start-type>). Find the number of
            # lines since the <start-type> line, add that to the end line
            # like ("end", <start-type>, <distance>).
            line.record_count = (lineno - starts[line.start_record_type]) + 1

        result.append(line)

    return result


def format_line(line: chieftypes._Record) -> str:
    """Format a line, with `None` values as the empty string."""
    values = dataclasses.astuple(line)
    return FIELD_SEP.join("" if v is None else str(v) for v in values)


def format_lines(lines: typing.Sequence[chieftypes._Record]) -> str:
    """Format the sequence of line tuples as 1 complete string."""
    lines = resolve_line_numbers(lines)
    formatted_lines = [format_line(line) for line in lines]

    return LINE_SEP.join(formatted_lines) + LINE_SEP


def count_transactions(lines: typing.Sequence[chieftypes._Record]) -> int:
    """Count of licence transactions, for use on the `fileTrailer` line."""
    # A transaction is any line  with "licence" as the first field (ignoring
    # line numbers).
    return sum(line.type_ == chieftypes.Licence.type_ for line in lines)

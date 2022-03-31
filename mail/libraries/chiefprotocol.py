# The CHIEF message protocol(s). "TIS" means technical interface specification.
# DES235: TIS LINE FILE DIALOGUE AND SYNTAX
# DES236: TIS – Licence Maintenance and Usage
#
# TIS spec jargon:
# - M: mandatory (required)
# - O: optional
# - C: conditional
# - A: absent (must not be present)


import typing


def resolve_line_numbers(lines: typing.Sequence[tuple]) -> list:
    """Add line numbers for a CHIEF message.

    For "end" lines, we keep track of the number of lines since the matching
    opening line type, and add that number to the end of the line.
    """
    starts = {}
    result = []

    for lineno, line in enumerate(lines, start=1):
        line_type = line[0]
        # Track the most recent line number for each line type.
        starts[line_type] = lineno

        if line_type == "end":
            # End lines are like ("end", <start-type>). Find the number of
            # lines since the <start-type> line, add that to the end line
            # like ("end", <start-type>, <distance>).
            start_type = line[1]
            distance = (lineno - starts[start_type]) + 1
            line += (distance,)

        # Prepend every line with the line number.
        line = (lineno,) + line
        result.append(line)

    return result


def format_line(line: tuple) -> str:
    """Format a line, with `None` values as the empty string."""
    field_sep = "\\"  # A single back-slash character.

    return field_sep.join("" if v is None else str(v) for v in line)


def format_lines(lines: typing.Sequence[tuple]) -> str:
    """Format the sequence of line tuples as 1 complete string."""
    lines = resolve_line_numbers(lines)
    formatted_lines = [format_line(line) for line in lines]
    line_sep = "\n"

    return line_sep.join(formatted_lines) + line_sep


def count_transactions(lines: typing.Sequence[tuple]) -> int:
    """Count of licence transactions, for use on the `fileTrailer` line."""
    # A transaction is any line  with "licence" as the first field (ignoring
    # line numbers).
    return sum(line[0] == "licence" for line in lines)

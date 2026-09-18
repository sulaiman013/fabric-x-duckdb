"""
Tests for the test_decoding payload parser.

  python test_cdc_parser.py

The parser is the riskiest part of the CDC path. test_decoding emits changes as
`name[type]:value`, where text values are single quoted with doubled internal
quotes. This dataset is deliberately full of commas, quotes, brackets and
padding inside values, so a naive split on spaces or a regex over the whole
payload silently corrupts rows. These cases are the ones that break such an
implementation.
"""

import sys

from cdc_to_fabric import CHANGE_RE, parse_tuple

CASES = [
    (
        "plain values and a null",
        "a[text]:'simple' b[text]:null",
        {"a": "simple", "b": None},
    ),
    (
        "commas and spaces inside values",
        "narrative[text]:'POS PURCHASE, KUALA LUMPUR MY' amt[text]:'1,234.50'",
        {"narrative": "POS PURCHASE, KUALA LUMPUR MY", "amt": "1,234.50"},
    ),
    (
        "doubled single quotes are an escaped quote",
        "d[text]:'ATM CASH WD ''MBB KLCC''' e[text]:'x'",
        {"d": "ATM CASH WD 'MBB KLCC'", "e": "x"},
    ),
    (
        "empty string is not null",
        "f[text]:'' g[text]:null",
        {"f": "", "g": None},
    ),
    (
        "a value that looks like a column spec",
        "h[text]:'weird[text]:value' i[bigint]:42",
        {"h": "weird[text]:value", "i": "42"},
    ),
    (
        "padding and parenthesised negatives survive intact",
        "j[text]:'  padded  ' k[text]:'(45.00)'",
        {"j": "  padded  ", "k": "(45.00)"},
    ),
    (
        "DELETE emits key columns only",
        "_mirror_row_id[bigint]:123",
        {"_mirror_row_id": "123"},
    ),
]


def main():
    failures = 0
    for name, payload, expected in CASES:
        got = parse_tuple(payload)
        if got == expected:
            print("ok    %s" % name)
        else:
            failures += 1
            print("FAIL  %s" % name)
            print("        payload  : %s" % payload)
            print("        expected : %r" % expected)
            print("        got      : %r" % got)

    line = "table landing.raw_txn: UPDATE: a[text]:'1' b[text]:null"
    m = CHANGE_RE.match(line)
    if m and m.groups()[:3] == ("landing", "raw_txn", "UPDATE"):
        print("ok    change header regex")
    else:
        failures += 1
        print("FAIL  change header regex -> %r" % (m.groups() if m else None))

    total = len(CASES) + 1
    print("\n%d/%d passed" % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

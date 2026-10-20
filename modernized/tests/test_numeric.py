from __future__ import annotations

from decimal import Decimal

import pytest

from account_system import (
    INITIAL_BALANCE,
    MAX_BALANCE,
    fit_balance,
    format_amount,
    parse_amount,
    parse_choice,
)


def test_domain_constants() -> None:
    assert INITIAL_BALANCE == Decimal("1000.00")
    assert MAX_BALANCE == Decimal("999999.99")


# RULE-005 runtime probes (RULES.md).
@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("1", 1),
        ("2", 2),
        ("3", 3),
        ("4", 4),
        ("12", 1),
        ("1x", 1),
        ("3a", 3),
        ("0", None),
        ("5", None),
        ("9", None),
        ("x", None),
        (" 1", None),
        ("-1", None),
        ("+1", None),
        ("", None),
    ],
)
def test_parse_choice(line: str, expected: int | None) -> None:
    assert parse_choice(line) == expected


# RULE-014 runtime probes (RULES.md table); expected is the amount the legacy program used.
@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("500", "500.00"),
        ("1.5", "1.50"),
        (".5", "0.50"),
        ("12.345", "12.34"),
        ("99999.999", "99999.99"),
        ("999999.99", "999999.90"),
        ("123456.78", "123456.70"),
        ("000000.01", "0.00"),
        ("1234567.89", "234567.00"),
        ("12345678", "345678.00"),
        ("-50", "50.00"),
        ("+5", "5.00"),
        (" 5", "5.00"),
        ("5 ", "5.00"),
        ("1,5", "15.00"),
        ("abc", "0.00"),
        ("12a", "0.00"),
        ("a12", "0.00"),
        ("1e3", "0.00"),
        ("5-", "0.00"),
        ("", "0.00"),
        ("1000.001", "1000.00"),
        ("0.01", "0.01"),
        # Differential-corpus findings (RULES.md RULE-014, amended).
        ("1 2", "12.00"),
        ("6 .55", "6.55"),
        ("92,005 1811", "920051.00"),
        ("2. 2 ", "2.20"),
        ("+3 5", "35.00"),
        (".3148a5.-2", "0.31"),
        ("5 .435..215", "5.43"),
        ("+33.27-9...3", "33.27"),
        ("1.2.3", "0.00"),
        ("..5", "0.00"),
        ("1.2-", "0.00"),
        ("1 a", "0.00"),
        ("+", "0.00"),
        (" 1234567", "234567.00"),
        (" -5", "5.00"),
        ("+,5", "5.00"),
        (",+5", "0.00"),
        (",+231,", "0.00"),
        ("a1234567", "234567.00"),
        ("*0000001", "1.00"),
        ("a123456", "0.00"),
        ("9a234567", "0.00"),
        (".1234567", "0.12"),
    ],
)
def test_parse_amount(line: str, expected: str) -> None:
    assert parse_amount(line) == Decimal(expected)


def test_parse_amount_rejects_non_ascii_digits() -> None:
    assert parse_amount("\u00b2") == Decimal("0.00")


# RULE-010 overflow probes: balance 1000.00 + amount.
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1500.00", "1500.00"),
        ("100999.99", "100999.99"),
        ("999999.99", "999999.99"),
        ("1000000.00", "0.00"),
        ("1000999.00", "999.00"),
        ("1000999.90", "999.90"),
    ],
)
def test_fit_balance(value: str, expected: str) -> None:
    assert fit_balance(Decimal(value)) == Decimal(expected)


# RULE-017 with intentional change D2.
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1000", "1000.00"),
        ("0", "0.00"),
        ("0.5", "0.50"),
        ("999999.99", "999999.99"),
        ("1050.00", "1050.00"),
    ],
)
def test_format_amount(value: str, expected: str) -> None:
    assert format_amount(Decimal(value)) == expected

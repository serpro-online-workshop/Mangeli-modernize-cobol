"""Differential tests of numeric semantics against the compiled GnuCOBOL legacy binary (D1)."""

from __future__ import annotations

import random
import re
from decimal import Decimal

import pytest

from account_system import INITIAL_BALANCE, fit_balance, parse_amount, parse_choice

pytestmark = pytest.mark.differential

_CREDIT_RESULT = re.compile(r"Amount credited\. New balance: (\d{6}\.\d{2})")
_CORPUS_SEED = 20261020
_CORPUS_SIZE = 250
_CORPUS_ALPHABET = "0123456789+-., ab*\t\r\x0b\u00e9"

RULE_005_CASES = ["1", "2", "3", "4", "12", "1x", "3a", "0", "5", "9", "x", " 1", "-1", "+1", ""]
RULE_014_CASES = [
    "500",
    "1.5",
    ".5",
    "12.345",
    "99999.999",
    "999999.99",
    "123456.78",
    "000000.01",
    "1234567.89",
    "12345678",
    "-50",
    "+5",
    " 5",
    "5 ",
    "1,5",
    "abc",
    "12a",
    "a12",
    "1e3",
    "5-",
    "",
    "1000.001",
    "0.01",
    "999000",
    "999999",
    ".",
    "..5",
    "1.2.3",
    "1 2",
    "+-5",
    "--5",
    ",5",
    "5.",
    "  ",
    "00000000",
    "999999999",
    "+999999.99",
    "-.01",
    "6 .55",
    "2. 2 ",
    ".3148a5.-2",
    "5 .435..215",
    "1.2.",
    ".1.2",
    "1..2",
    "1.2-",
    " +5",
    " -5",
    ",+5",
    "+ 5",
    "+,5",
    "+.5",
    ",+231,",
    "a1234567",
    "a123456",
    "a12345678",
    "1a234567",
    "1234567a",
    "a0000001",
    "*1234567",
    ".1234567",
    "a123,456",
    "a12345 6",
    "9a234567",
    "a1234567.5",
    "\t+5",
    "1\t2",
    "\x0c5",
    "12\r34",
    "5\x00",
    "\u00e91234567",
    "1.23\u00e9",
    "\u00e9\u00e9\u00e912345",
]


def _generated_corpus() -> list[str]:
    rng = random.Random(_CORPUS_SEED)  # noqa: S311 - deterministic test data, not security
    return [
        "".join(rng.choice(_CORPUS_ALPHABET) for _ in range(rng.randint(0, 12)))
        for _ in range(_CORPUS_SIZE)
    ]


def _legacy_choice(legacy_app, line: str) -> int | None:
    # "0" answers an amount prompt if options 2/3 were taken; "4" then exits.
    output = legacy_app.run(f"{line}\n0\n4\n")
    after_first_prompt = output.split("Enter your choice (1-4): \n", 1)[1]
    first_reaction = after_first_prompt.splitlines()[0]
    reactions = {
        "Current balance": 1,
        "Enter credit amount": 2,
        "Enter debit amount": 3,
        "Exiting the program": 4,
    }
    for prefix, choice in reactions.items():
        if first_reaction.startswith(prefix):
            return choice
    assert first_reaction == "Invalid choice, please select 1-4."
    return None


def _legacy_credit_balance(legacy_app, line: str) -> Decimal:
    match = _CREDIT_RESULT.search(legacy_app.run(f"2\n{line}\n4\n"))
    assert match is not None
    return Decimal(match.group(1))


@pytest.mark.parametrize("line", RULE_005_CASES)
def test_parse_choice_matches_legacy(legacy_app, line: str) -> None:
    assert parse_choice(line) == _legacy_choice(legacy_app, line)


@pytest.mark.parametrize("line", RULE_014_CASES + _generated_corpus())
def test_credit_amount_matches_legacy(legacy_app, line: str) -> None:
    expected = _legacy_credit_balance(legacy_app, line)
    assert fit_balance(INITIAL_BALANCE + parse_amount(line)) == expected

"""Account management console, modernized from src/cobol (MainProgram, Operations, DataProgram).

Rule IDs refer to analysis/account-system/RULES.md; design in analysis/account-system/DESIGN.md.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

CENT = Decimal("0.01")
INITIAL_BALANCE = Decimal("1000.00")
MAX_BALANCE = Decimal("999999.99")

# PIC 9(6)V99 holds 8 digit positions; GnuCOBOL ACCEPT reads only that many input characters.
_AMOUNT_INPUT_WIDTH = 8
_INTEGER_DIGITS = 6
_FRACTION_DIGITS = 2
_PIC_MODULUS = Decimal(10**_INTEGER_DIGITS)
_ASCII_DIGITS = frozenset("0123456789")


def _truncate_to_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_DOWN)


def parse_choice(line: str) -> int | None:
    """Menu choice as read into PIC 9: only the first character counts (RULE-005)."""
    first = line[:1]
    if first in ("1", "2", "3", "4"):
        return int(first)
    return None


def parse_amount(line: str) -> Decimal:
    """Amount as GnuCOBOL ACCEPTs it into unsigned PIC 9(6)V99 (RULE-014). Never raises."""
    window = line[:_AMOUNT_INPUT_WIDTH]
    # GnuCOBOL ignores any first character (except '.') when the other 7 positions are digits.
    tail = window[1:]
    if len(window) == _AMOUNT_INPUT_WIDTH and window[0] != "." and set(tail) <= _ASCII_DIGITS:
        return Decimal(f"{tail[-_INTEGER_DIGITS:]}.00")
    text = window.lstrip(" ")
    # A sign is accepted only before any digit or comma; spaces and commas are ignored elsewhere.
    if text[:1] in ("+", "-"):
        text = text[1:]
    text = text.replace(" ", "").replace(",", "")
    integer_digits = ""
    fraction_digits = ""
    seen_point = False
    for char in text:
        if char not in _ASCII_DIGITS and (seen_point or char != "."):
            return Decimal("0.00")
        if char == ".":
            seen_point = True
        elif seen_point:
            fraction_digits += char
            # GnuCOBOL stops validating once the 2 decimal positions are filled.
            if len(fraction_digits) == _FRACTION_DIGITS:
                break
        else:
            integer_digits += char
    if not integer_digits and not fraction_digits:
        return Decimal("0.00")
    integer_part = integer_digits[-_INTEGER_DIGITS:] or "0"
    fraction_part = fraction_digits.ljust(_FRACTION_DIGITS, "0")
    return Decimal(f"{integer_part}.{fraction_part}")


def fit_balance(value: Decimal) -> Decimal:
    """Store into PIC 9(6)V99 without ON SIZE ERROR: high-order digits are dropped (RULE-010)."""
    return _truncate_to_cents(abs(value) % _PIC_MODULUS)


def format_amount(value: Decimal) -> str:
    """Two decimals without zero padding (intentional change D2 / RULE-017)."""
    return str(_truncate_to_cents(value))

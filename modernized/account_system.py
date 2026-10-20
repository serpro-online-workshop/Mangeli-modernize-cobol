"""Account management console, modernized from src/cobol (MainProgram, Operations, DataProgram).

Rule IDs refer to analysis/account-system/RULES.md; design in analysis/account-system/DESIGN.md.
"""

from __future__ import annotations

import sys
from decimal import ROUND_DOWN, Decimal
from typing import TextIO

CENT = Decimal("0.01")
INITIAL_BALANCE = Decimal("1000.00")
MAX_BALANCE = Decimal("999999.99")

# PIC 9(6)V99 holds 8 digit positions; GnuCOBOL ACCEPT reads only that many input bytes.
_AMOUNT_INPUT_WIDTH = 8
_INTEGER_DIGITS = 6
_FRACTION_DIGITS = 2
_PIC_MODULUS = Decimal(10**_INTEGER_DIGITS)
_ASCII_DIGITS = frozenset("0123456789")
# Characters GnuCOBOL skips inside a numeric ACCEPT, measured against the legacy binary.
_IGNORED_BLANKS = " \t\v\f\r"
# Only the first 8 bytes of a line matter; the rest is read in chunks and discarded.
_READ_CHUNK = 64

MENU_LINES = (
    "--------------------------------",
    "Account Management System",
    "1. View Balance",
    "2. Credit Account",
    "3. Debit Account",
    "4. Exit",
    "--------------------------------",
    "Enter your choice (1-4): ",
)
INVALID_CHOICE = "Invalid choice, please select 1-4."
GOODBYE = "Exiting the program. Goodbye!"


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
    # GnuCOBOL counts bytes, not characters; latin-1 maps each byte back to one character.
    try:
        raw = line.encode("utf-8", "surrogateescape")
    except UnicodeEncodeError:
        raw = line.encode("utf-8", "replace")
    window = raw[:_AMOUNT_INPUT_WIDTH].decode("latin-1")
    # GnuCOBOL ignores any first character (except '.') when the other 7 positions are digits.
    tail = window[1:]
    if len(window) == _AMOUNT_INPUT_WIDTH and window[0] != "." and set(tail) <= _ASCII_DIGITS:
        return Decimal(f"{tail[-_INTEGER_DIGITS:]}.00")
    text = window.lstrip(_IGNORED_BLANKS)
    # A sign is accepted only before any digit or comma; blanks and commas are ignored elsewhere.
    if text[:1] in ("+", "-"):
        text = text[1:]
    text = "".join(char for char in text if char not in _IGNORED_BLANKS and char != ",")
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
    if value < 0:
        raise ValueError(f"balance cannot be negative: {value}")
    return _truncate_to_cents(value % _PIC_MODULUS)


def format_amount(value: Decimal) -> str:
    """Two decimals without zero padding (intentional change D2 / RULE-017)."""
    return str(_truncate_to_cents(value))


class BalanceStore:
    """In-memory balance, reset on every run (DataProgram; RULE-001, RULE-016, D5)."""

    def __init__(self) -> None:
        self._balance = INITIAL_BALANCE

    def read(self) -> Decimal:
        return self._balance

    def write(self, value: Decimal) -> None:
        self._balance = fit_balance(value)


def _say(out: TextIO, text: str) -> None:
    out.write(text + "\n")


def _read_line(inp: TextIO) -> str | None:
    """Next input line without its newline, or None at end of input. Memory is bounded."""
    head = inp.readline(_READ_CHUNK)
    if head == "":
        return None
    chunk = head
    while chunk and not chunk.endswith("\n"):
        chunk = inp.readline(_READ_CHUNK)
    return head.rstrip("\n")


def view_balance(store: BalanceStore, out: TextIO) -> None:
    """RULE-008."""
    _say(out, f"Current balance: {format_amount(store.read())}")


def credit(store: BalanceStore, inp: TextIO, out: TextIO) -> None:
    """RULE-009, RULE-010, RULE-015. End of input reads as an empty amount (0.00)."""
    _say(out, "Enter credit amount: ")
    amount = parse_amount(_read_line(inp) or "")
    store.write(store.read() + amount)
    _say(out, f"Amount credited. New balance: {format_amount(store.read())}")


def debit(store: BalanceStore, inp: TextIO, out: TextIO) -> None:
    """RULE-011, RULE-012, RULE-013, RULE-015. End of input reads as an empty amount (0.00)."""
    _say(out, "Enter debit amount: ")
    amount = parse_amount(_read_line(inp) or "")
    balance = store.read()
    if balance >= amount:
        store.write(balance - amount)
        _say(out, f"Amount debited. New balance: {format_amount(store.read())}")
    else:
        _say(out, "Insufficient funds for this debit.")


def run(inp: TextIO, out: TextIO) -> int:
    """Menu loop (MainProgram; RULE-003..007). End of input at the menu exits like option 4 (D8)."""
    store = BalanceStore()
    while True:
        for menu_line in MENU_LINES:
            _say(out, menu_line)
        line = _read_line(inp)
        if line is None:
            break
        choice = parse_choice(line)
        if choice == 1:
            view_balance(store, out)
        elif choice == 2:
            credit(store, inp, out)
        elif choice == 3:
            debit(store, inp, out)
        elif choice == 4:
            break
        else:
            _say(out, INVALID_CHOICE)
    _say(out, GOODBYE)
    return 0


def main() -> int:
    # Keep invalid UTF-8 bytes and lone '\r' intact: both are significant to RULE-014.
    sys.stdin.reconfigure(errors="surrogateescape", newline="\n")
    return run(sys.stdin, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())

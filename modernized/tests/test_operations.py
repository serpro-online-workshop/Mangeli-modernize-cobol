from __future__ import annotations

import io
from decimal import Decimal

import pytest

from account_system import BalanceStore, credit, debit, view_balance


def _store_with(balance: str) -> BalanceStore:
    store = BalanceStore()
    store.write(Decimal(balance))
    return store


def test_store_starts_at_initial_balance() -> None:
    # RULE-001
    assert BalanceStore().read() == Decimal("1000.00")


def test_store_keeps_written_value_and_new_store_resets() -> None:
    # RULE-016, D5
    store = BalanceStore()
    store.write(Decimal("1050.00"))
    assert store.read() == Decimal("1050.00")
    assert BalanceStore().read() == Decimal("1000.00")


def test_store_write_applies_pic_overflow() -> None:
    # RULE-002, RULE-010
    store = BalanceStore()
    store.write(Decimal("1000999.99"))
    assert store.read() == Decimal("999.99")


def test_view_balance_does_not_change_balance() -> None:
    # RULE-008
    store = _store_with("1050.00")
    out = io.StringIO()
    view_balance(store, out)
    assert out.getvalue() == "Current balance: 1050.00\n"
    assert store.read() == Decimal("1050.00")


@pytest.mark.parametrize(
    ("start", "line", "expected_balance"),
    [
        ("1000.00", "500\n", "1500.00"),  # RULE-009
        ("1000.00", "0\n", "1000.00"),  # RULE-009 zero credit still reported
        ("1000.00", "999000\n", "0.00"),  # RULE-010
        ("1000.00", "999999\n", "999.00"),  # RULE-010
        ("1000.00", "-50\n", "1050.00"),  # RULE-014 sign dropped
        ("1000.00", "abc\n", "1000.00"),  # RULE-014 invalid -> 0
        ("1000.00", "", "1000.00"),  # end of input reads as empty amount
    ],
)
def test_credit(start: str, line: str, expected_balance: str) -> None:
    store = _store_with(start)
    out = io.StringIO()
    credit(store, io.StringIO(line), out)
    assert out.getvalue() == (
        f"Enter credit amount: \nAmount credited. New balance: {expected_balance}\n"
    )
    assert store.read() == Decimal(expected_balance)


@pytest.mark.parametrize(
    ("start", "line", "expected_balance"),
    [
        ("1100.00", "50\n", "1050.00"),  # RULE-012
        ("1000.00", "1000\n", "0.00"),  # RULE-011 equality allowed
        ("1000.00", "0\n", "1000.00"),  # RULE-012 zero debit
        ("1000.00", "-50\n", "950.00"),  # RULE-014 sign dropped
        ("1000.00", "1000.001\n", "0.00"),  # RULE-014 truncation
        ("0.00", "0\n", "0.00"),  # RULE-015 prompt shown at zero balance
    ],
)
def test_debit_success(start: str, line: str, expected_balance: str) -> None:
    store = _store_with(start)
    out = io.StringIO()
    debit(store, io.StringIO(line), out)
    assert out.getvalue() == (
        f"Enter debit amount: \nAmount debited. New balance: {expected_balance}\n"
    )
    assert store.read() == Decimal(expected_balance)


@pytest.mark.parametrize(("start", "line"), [("1000.00", "2000\n"), ("1000.00", "1000.01\n")])
def test_debit_insufficient_funds_keeps_balance(start: str, line: str) -> None:
    # RULE-011, RULE-013
    store = _store_with(start)
    out = io.StringIO()
    debit(store, io.StringIO(line), out)
    assert out.getvalue() == "Enter debit amount: \nInsufficient funds for this debit.\n"
    assert store.read() == Decimal(start)

from __future__ import annotations

import io

import pytest
from conftest import run_modern_process

from account_system import GOODBYE, INVALID_CHOICE, MENU_LINES, main, run

MENU = "".join(line + "\n" for line in MENU_LINES)
BYE = GOODBYE + "\n"


def _session(script: str) -> tuple[int, str]:
    out = io.StringIO()
    code = run(io.StringIO(script), out)
    return code, out.getvalue()


def test_exit_immediately() -> None:
    # RULE-003, RULE-007
    assert _session("4\n") == (0, MENU + BYE)


def test_view_credit_debit_sequence_keeps_state() -> None:
    # RULE-004, RULE-016; transcript lines measured on the legacy binary (D2 applied).
    code, output = _session("2\n100\n3\n50\n1\n4\n")
    assert code == 0
    assert output == (
        MENU
        + "Enter credit amount: \nAmount credited. New balance: 1100.00\n"
        + MENU
        + "Enter debit amount: \nAmount debited. New balance: 1050.00\n"
        + MENU
        + "Current balance: 1050.00\n"
        + MENU
        + BYE
    )


def test_insufficient_funds_in_session() -> None:
    # RULE-013
    _, output = _session("3\n2000\n1\n4\n")
    assert "Insufficient funds for this debit.\n" + MENU + "Current balance: 1000.00\n" in output


@pytest.mark.parametrize("choice", ["9", "0", "x", "", " 1", "-1"])
def test_invalid_choice_redisplays_menu(choice: str) -> None:
    # RULE-005, RULE-006
    assert _session(f"{choice}\n4\n") == (0, MENU + INVALID_CHOICE + "\n" + MENU + BYE)


def test_multi_digit_choice_uses_first_digit() -> None:
    # RULE-005
    assert _session("12\n4\n") == (0, MENU + "Current balance: 1000.00\n" + MENU + BYE)


def test_end_of_input_at_menu_says_goodbye() -> None:
    # RULE-018 changed by D8: no endless loop.
    assert _session("") == (0, MENU + BYE)
    assert _session("1") == (0, MENU + "Current balance: 1000.00\n" + MENU + BYE)


def test_end_of_input_at_amount_reads_zero_then_goodbye() -> None:
    _, output = _session("2\n")
    assert output == (
        MENU + "Enter credit amount: \nAmount credited. New balance: 1000.00\n" + MENU + BYE
    )


def test_long_lines_are_consumed_whole() -> None:
    # HARDENING F5: legacy reads the whole line and uses only its first positions.
    _, output = _session("2\n" + "5" * 300 + "\n1" + "x" * 5000 + "\n4\n")
    assert "Amount credited. New balance: 556555.00\n" in output
    assert "Current balance: 556555.00\n" in output
    assert output.endswith(MENU + BYE)


def test_crlf_input() -> None:
    _, output = _session("2\r\n50\r\n1\r\n4\r\n")
    assert "Amount credited. New balance: 1050.00\n" in output
    assert "Current balance: 1050.00\n" in output


def test_main_uses_process_stdio() -> None:
    assert run_modern_process("1\n4\n") == MENU + "Current balance: 1000.00\n" + MENU + BYE


def test_main_preserves_invalid_utf8_and_carriage_return(monkeypatch) -> None:
    raw = io.BytesIO(b"2\n\xff1234567\n2\n12\r34\n1\n4\n")
    stdin = io.TextIOWrapper(raw, encoding="utf-8")
    stdout = io.StringIO()
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", stdout)
    assert main() == 0
    assert "Amount credited. New balance: 235567.00\n" in stdout.getvalue()
    assert "Amount credited. New balance: 236801.00\n" in stdout.getvalue()

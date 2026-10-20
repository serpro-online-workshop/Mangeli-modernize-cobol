"""Whole-session differential tests: legacy transcript vs Python process (D1, D2)."""

from __future__ import annotations

import random
import re
from decimal import Decimal

import pytest
from conftest import run_modern_process

from account_system import format_amount

pytestmark = pytest.mark.differential

# The only allowed normalization: legacy PIC 9(6)V99 display -> unpadded amount (D2).
_LEGACY_AMOUNT = re.compile(r"\b\d{6}\.\d{2}\b")
_SESSION_SEED = 20261021
_SESSION_COUNT = 60
_MENU_TOKENS = ["1", "2", "3", "9", "x", "12", "", " 1", "3a"]
_AMOUNT_TOKENS = ["500", "0", "1000", "2000", "-50", "12.345", "999000", "abc", "\t5", "1,5", ""]

# Every script ends with "4": the legacy binary never stops at end of input (RULE-018).
RECORDED_SESSIONS = {
    "exit": "4\n",
    "view": "1\n4\n",
    "credit_debit_view": "2\n100\n3\n50\n1\n4\n",
    "insufficient": "3\n2000\n1\n4\n",
    "debit_all": "3\n1000\n1\n4\n",
    "overflow": "2\n999000\n1\n4\n",
    "invalid_choices": "9\n0\nx\n\n 1\n-1\n+1\n4\n",
    "multi_digit_choice": "12\n4\n",
    "choice_with_letter": "3a\n50\n4\n",
    "crlf": "2\r\n50\r\n1\r\n4\r\n",
    "long_lines": "2\n" + "5" * 300 + "\n1" + "x" * 5000 + "\n4\n",
    "repeated_credits": "2\n999999.99\n2\n0.01\n1\n4\n",
}


def _normalize_legacy(output: str) -> str:
    return _LEGACY_AMOUNT.sub(lambda m: format_amount(Decimal(m.group())), output)


def _generated_sessions() -> list[str]:
    rng = random.Random(_SESSION_SEED)  # noqa: S311 - deterministic test data, not security
    sessions = []
    for _ in range(_SESSION_COUNT):
        lines = []
        for _ in range(rng.randint(1, 8)):
            token = rng.choice(_MENU_TOKENS)
            lines.append(token)
            if token[:1] in ("2", "3"):
                lines.append(rng.choice(_AMOUNT_TOKENS))
        lines.append("4")
        sessions.append("\n".join(lines) + "\n")
    return sessions


@pytest.mark.parametrize("script", RECORDED_SESSIONS.values(), ids=RECORDED_SESSIONS.keys())
def test_recorded_session_matches_legacy(legacy_app, script: str) -> None:
    assert run_modern_process(script) == _normalize_legacy(legacy_app.run(script))


@pytest.mark.parametrize("script", _generated_sessions())
def test_generated_session_matches_legacy(legacy_app, script: str) -> None:
    assert run_modern_process(script) == _normalize_legacy(legacy_app.run(script))

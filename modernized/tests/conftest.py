from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "modernized" / "account_system.py"
LEGACY_SOURCES = [
    REPO_ROOT / "src" / "cobol" / name for name in ("main.cob", "operations.cob", "data.cob")
]
# Legacy loops forever on EOF (RULE-018); scripts must end with "4" and runs are time-bounded.
LEGACY_TIMEOUT_SECONDS = 5


def _run_process(command: list[str], script: str) -> str:
    result = subprocess.run(
        command,
        input=script.encode("utf-8", "surrogateescape"),
        capture_output=True,
        timeout=LEGACY_TIMEOUT_SECONDS,
        check=True,
    )
    return result.stdout.decode("utf-8", "surrogateescape")


class LegacyApp:
    def __init__(self, binary: Path) -> None:
        self._binary = binary

    def run(self, script: str) -> str:
        return _run_process([str(self._binary)], script)


def run_modern_process(script: str) -> str:
    """Run the Python app as a real process so stdin decoding matches production."""
    return _run_process([sys.executable, str(MODULE_PATH)], script)


@pytest.fixture(scope="session")
def legacy_app(tmp_path_factory: pytest.TempPathFactory) -> LegacyApp:
    cobc = shutil.which("cobc")
    if cobc is None:
        pytest.skip("GnuCOBOL (cobc) not installed; differential oracle unavailable")
    binary = tmp_path_factory.mktemp("legacy") / "accountsystem"
    subprocess.run(
        [cobc, "-x", *map(str, LEGACY_SOURCES), "-o", str(binary)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return LegacyApp(binary)

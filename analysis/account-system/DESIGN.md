# Modernization Design — account-system

## Source Inputs

- Brief: [BRIEF.md](BRIEF.md) — decisions D1–D7.
- Assessment: [ASSESSMENT.md](ASSESSMENT.md) — risks R1–R10, runtime probes.
- Rules: [RULES.md](RULES.md) — RULE-001 … RULE-018.
- Map: [MAP.md](MAP.md), [MAP.mmd](MAP.mmd) — single module, slices 0–4.
- Target stack: Python 3.10, standard library only, `decimal.Decimal`, `pytest` + `pytest-cov`, `ruff` (`.github/copilot-instructions.md`).

## Design Summary

- Target architecture: one console module `modernized/account_system.py` with four internal layers — numeric semantics (pure functions), `BalanceStore`, operations, menu loop — and injectable text streams. No packaging (D6), no persistence (D5).
- Main migration approach: rewrite with a golden-master differential oracle from the compiled GnuCOBOL 3.1.2 binary (D1); legacy stays in `src/cobol/` as reference and rollback.

## Target APIs

All in `modernized/account_system.py`.

| API or interface | Purpose | Preserved behavior | Intentional change |
| --- | --- | --- | --- |
| `MAX_BALANCE = Decimal("999999.99")`, `INITIAL_BALANCE = Decimal("1000.00")`, `CENT = Decimal("0.01")` | Domain constants | RULE-001, RULE-002 | — |
| `parse_choice(line: str) -> int \| None` | Menu input | RULE-005: first character only; `1`–`4` → int, anything else → `None` | — |
| `parse_amount(line: str) -> Decimal` | Amount input | RULE-014 steps 1–6 exactly (first 8 chars, leading sign dropped, `,` ignored, truncate decimals, low-order 6 integer digits, invalid → `0.00`); never raises | — |
| `fit_balance(value: Decimal) -> Decimal` | `PIC 9(6)V99` store | RULE-010: `value % 1_000_000` truncated to 2 places (`ROUND_DOWN`) | — |
| `format_amount(value: Decimal) -> str` | Display | Two decimals always | **D2**: no zero padding (`1000.00`, `0.00`) |
| `class BalanceStore` — `read() -> Decimal`, `write(value: Decimal) -> None` | Account state (DataProgram) | RULE-001, RULE-016; in-memory per instance | — |
| `view_balance(store, out)` | Option 1 | RULE-008 message `Current balance: <amount>` | D2 format |
| `credit(store, inp, out)` | Option 2 | RULE-009, RULE-010, RULE-015; prompt `Enter credit amount: ` then read, add, fit, write, `Amount credited. New balance: <amount>` | D2 format |
| `debit(store, inp, out)` | Option 3 | RULE-011…013, RULE-015; `>=` check; `Amount debited. New balance: <amount>` or `Insufficient funds for this debit.` | D2 format |
| `run(inp: TextIO = sys.stdin, out: TextIO = sys.stdout) -> int` | Menu loop (MainProgram) | RULE-003, 004, 006, 007; returns 0 | **C2** EOF at menu → goodbye line, return 0 |
| `if __name__ == "__main__": sys.exit(run())` | Entry point | `python modernized/account_system.py` | Replaces `cobc -x` build |

### Console I/O contract (measured with `cat -A` on legacy output)

- Every `DISPLAY` is one line ending in `\n`, including prompts with their trailing space: `Enter your choice (1-4): \n`, `Enter credit amount: \n`, `Enter debit amount: \n`. Use `out.write(text + "\n")`, not `input(prompt)` (which omits the newline and writes to the terminal differently).
- Input is not echoed. Read one line in bounded 64-character chunks (rest of a long line is discarded, like legacy); strip only the trailing `\n`. stdin is reconfigured with `encoding="utf-8"`, `newline="\n"` and `errors="surrogateescape"` so `\r` and every input byte reach the parsers unchanged whatever the locale (RULE-014 counts bytes and treats `\r` as blank). Ctrl+C exits 130, a closed output pipe exits 141 silently, and a missing stdin counts as end of input (D8).
- Menu block (8 lines) is printed before every choice, exactly as RULE-003.
- Final line on option 4: `Exiting the program. Goodbye!`.

## Data Model

| Concept | Legacy source | Target model | Migration note |
| --- | --- | --- | --- |
| Balance | `STORAGE-BALANCE PIC 9(6)V99 VALUE 1000.00` (`data.cob` L6) | `Decimal`, quantized to `0.01`, invariant `0 <= b <= 999999.99`, held by `BalanceStore` | No data to migrate (D5) |
| Amount | `AMOUNT PIC 9(6)V99` (`operations.cob` L7) | `Decimal` from `parse_amount`, same invariant | — |
| Menu choice | `USER-CHOICE PIC 9` (`main.cob` L6) | `int \| None` | — |
| Continue flag | `CONTINUE-FLAG PIC X(3)` | local loop control | Retired as data |
| Operation code | `'TOTAL '`/`'CREDIT'`/`'DEBIT '`, `'READ'`/`'WRITE'` | direct function calls / methods | Retired (no observable effect) |

Arithmetic uses a local `decimal.Context` with `rounding=ROUND_DOWN`; no `float` anywhere in money paths.

## Runtime and Deployment Model

- Runtime: CPython 3.10 (3.10.12 verified locally); no third-party runtime dependencies.
- Deployment model: run locally with `python modernized/account_system.py`; no service, container, or installer (D6).
- Configuration: none. Dev-only tools: `pytest`, `pytest-cov`, `ruff` (`target-version = "py310"`), declared in `modernized/requirements-dev.txt`; ruff/pytest settings in `modernized/ruff.toml` and `modernized/pytest.ini` (not `pyproject.toml`, to respect D6).

## Observability

- Logs: none. stdout is the business contract; adding logs there would break transcripts. Any diagnostics would go to stderr and are out of scope.
- Metrics / Traces / Alerts: not applicable (single-user local console, no service).

## Security

- Identity / Authorization: none in legacy or target (single local user).
- Secrets: none.
- Data protection: no real data; balance is synthetic and in memory only.
- Input handling: `parse_amount`/`parse_choice` are total functions over arbitrary strings (no `eval`, no `float`, no exceptions), bounded to the first 8/1 characters — removes crash and resource risks while preserving RULE-014/005.
- Availability: legacy EOF loop (RULE-018) is addressed by C2.

## Migration Phases

| Phase | Scope | Entry criteria | Exit criteria | Rollback |
| --- | --- | --- | --- | --- |
| 0 | Golden-master harness: input scripts in `modernized/tests/golden/*.in`; test compiles `src/cobol` with `cobc` into `tmp_path`, runs each script, compares with Python after normalization; skips if `cobc` absent | This design approved | Every RULE example has a script; scripts end with `4` | Remove harness |
| 1 | `parse_choice`, `parse_amount`, `fit_balance`, `format_amount` + unit tests | Phase 0 | RULE-005/010/014/017 tests green | Revert module |
| 2 | `BalanceStore`, `view_balance`, `credit`, `debit` + unit tests | Phase 1 | RULE-001/002/008…013/015/016 green | Revert module |
| 3 | `run()`, entry point, session tests, differential suite | Phase 2; C2 approved (D8) | Differential suite equal; `ruff check` clean; 100% line coverage | Run `cobc` binary |
| 4 | `modernize-harden` + run instructions | Phase 3 | No open high findings | Revert docs |

Differential normalization (D2): in legacy output, replace every `\b\d{6}\.\d{2}\b` with `format_amount(Decimal(match))` before comparing. No other normalization is allowed.

## Behavioral Compatibility

### Behaviorally Identical

- Initial balance 1000.00, range 0.00–999999.99 (RULE-001, 002).
- Menu text, order, and prompts with trailing spaces; one line per message (RULE-003).
- Routing 1–4; first-character menu parsing; invalid message and re-display (RULE-004, 005, 006).
- Exit message and exit code 0 on option 4 (RULE-007).
- View, credit, debit messages verbatim; debit allowed when balance equals amount; insufficient funds leaves balance unchanged (RULE-008, 009, 011, 012, 013).
- Credit overflow wraps modulo 1,000,000 with no error (RULE-010, D4).
- Amount parsing quirks: 8-character window, sign dropped, comma ignored, truncation, invalid → 0 (RULE-014, D3).
- Amount prompt always shown before the balance check (RULE-015).
- State kept within a run, reset on every start (RULE-016, D5).

### Intentional Behavior Changes

| Change | Reason | Approval or SME question | Test implication |
| --- | --- | --- | --- |
| C1 — Amounts shown without zero padding (`1000.00` instead of `001000.00`) | Readability (D2) | **Approved** (BRIEF D2) | Differential normalization regex; unit tests assert unpadded format |
| C2 — On end of input at the menu prompt, print `Exiting the program. Goodbye!` and return exit code 0, instead of looping forever | Legacy hangs (RULE-018, ASSESSMENT R5); an endless loop cannot be tested or used non-interactively | **Approved** (BRIEF D8, 2026-10-20) | Session test with input lacking `4` must end with the menu block followed by the goodbye line and rc 0; differential scripts always end with `4`, so they are unaffected |

EOF while an amount is requested is **not** changed: `readline()` returns `""`, which `parse_amount` turns into `0.00` exactly like legacy empty input (RULE-014 step 6); the next menu read then hits C2.

## Design Challenge (critical review)

| Concern | Finding | Resolution |
| --- | --- | --- |
| Reproducing quirks (sign drop, 8-char window) may look like bugs to future maintainers | Real risk of "fixing" them later | Each quirk is named after its RULE in tests; deviations require a new decision in BRIEF |
| Parser derived from ~20 runtime samples | Unknown combinations (multiple `.`, embedded spaces, `+` with decimals) could diverge | Phase 0 adds a generated corpus (e.g. 200+ random strings from `[0-9+-., a]`, length 0–12) compared against legacy; any divergence becomes a RULE-014 amendment |
| Differential tests need GnuCOBOL | CI without `cobc` loses the oracle | Unit and session tests are authoritative and always run; differential suite marked and skipped with a clear reason |
| Single file mixes UI and logic | Could grow hard to test | Pure functions + injected streams keep each layer testable; split only via a recorded D6 change |
| `Decimal` default context (28 digits, half-even) | Silent rounding mismatch | Explicit `ROUND_DOWN` quantize everywhere values are fitted |
| Windows `\r\n` input | Could leak `\r` into parsing | Strip `\r\n` and `\n` only |

## Diagram Artifacts

- [`analysis/account-system/MAP.mmd`](MAP.mmd) — target layering and oracle; still valid for this design.
- [`analysis/account-system/ARCHITECTURE.mmd`](ARCHITECTURE.mmd) — legacy structure.

## Implementation Handoff

- First bounded slice for `modernize-transform`: **Phases 0 + 1** — golden-master harness and numeric semantics (`parse_choice`, `parse_amount`, `fit_balance`, `format_amount`), pinned by RULE-005/010/014/017 examples and the generated differential corpus.
- No open blockers (C2 approved as D8).

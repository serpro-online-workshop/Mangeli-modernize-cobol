# Hardening Review — account-system

Review 2 (2026-10-20) covers the complete application after DESIGN phases 2–3. Review 1 (phases 0–1) is kept below for traceability.

## Scope

- Target: `modernized/` — `account_system.py` (numeric semantics, `BalanceStore`, operations, `run`, `main`), `tests/` (7 files), `pytest.ini`, `ruff.toml`, `requirements-dev.txt`.
- Reviewed artifacts: [BRIEF.md](BRIEF.md) (D1–D8), [RULES.md](RULES.md) (RULE-001…018), [DESIGN.md](DESIGN.md), [MAP.md](MAP.md), Review 1 findings F1–F9; legacy `src/cobol/*.cob` compiled with GnuCOBOL 3.1.2 as oracle.

## Validation Commands

Run from `modernized/` with `.venv` (Python 3.10.12).

| Command | Result | Notes |
| --- | --- | --- |
| `../.venv/bin/pytest -q --cov=account_system --cov-branch --cov-report=term-missing` | 538 passed; 100% lines (118/118), 100% branches (40/40) | Includes 72 whole-session and 338 numeric differential cases against the legacy binary |
| `../.venv/bin/pytest -q -m "not differential"` | 128 passed, 410 deselected | Suite that runs without `cobc` |
| `../.venv/bin/ruff check .` / `ruff format --check .` | All checks passed / 7 files formatted | Project rule set |
| `../.venv/bin/ruff check --select ALL --ignore D,ANN,COM812,ISC001,T201,S101,S603,PLR2004,FBT,INP001,ERA001,PTH,EM,TRY003,N802 account_system.py` | All checks passed | Stricter one-off pass on production code |
| `python3 /tmp/fuzz_amount.py 5` / `13` | 0 / 3,000 mismatches each | Adds to 12,000 from transform (alphabet incl. tab, CR, VT, `é`) |
| `printf '2\n\xe91234567\n4\n' \| python account_system.py` (default UTF-8 locale, and `LC_ALL=C`) | `235567.00` = legacy | Raw byte preserved by `surrogateescape` |
| Same input with `PYTHONIOENCODING=latin-1` | `1000.00` ≠ legacy `235567.00` | **H1** |
| `yes 1 \| head -2000 \| python account_system.py \| head -1` | `BrokenPipeError` traceback, rc 1 | **H2** |
| `python account_system.py <&-` | `AttributeError: 'NoneType' object has no attribute 'reconfigure'` | **H2** |
| Ctrl+C (SIGINT) during input | `KeyboardInterrupt` traceback | **H2**; legacy prints `signal SIGINT` diagnostics |
| `pip-audit --version` | Not installed | F6 still open |
| `git diff --stat -- src/cobol` | Empty | Legacy untouched |

## Ranked Findings

| Rank | Severity | Area | Finding | Evidence | Recommendation | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | Medium | Behavior drift (RULE-014) | `main()` keeps the locale's stdin encoding. With a non-UTF-8 encoding (e.g. `PYTHONIOENCODING=latin-1` or an ISO-8859 locale), bytes are re-encoded differently and the 8-byte window diverges from legacy. | `\xe91234567`: legacy 235567.00, Python 1000.00 under latin-1; equal under UTF-8 and `LC_ALL=C` | Reconfigure stdin with `encoding="utf-8", errors="surrogateescape"`: this round-trips every byte regardless of locale; add a `main()` test with a latin-1 wrapper | Developer |
| H2 | Low | Error handling | Abnormal terminations show Python tracebacks: broken stdout pipe, closed stdin, Ctrl+C. Legacy also ends abnormally on SIGINT, so no rule is violated, but tracebacks leak internals and look like crashes. | Commands above | In `main()`, handle `KeyboardInterrupt` (exit 130) and `BrokenPipeError` (exit 141 / quiet), and fail with a one-line message when `sys.stdin` is `None`; add tests | Developer |
| H3 | Medium | Operational readiness | No run instructions or runbook for the Python app; README still describes the workshop and the workflow targeted Node.js. Required for cutover (DESIGN phase 4). | `README.md`, `.github/steps/4-convert-the-app.md` | Add a short "Run and test" section (Python 3.10, `python modernized/account_system.py`, venv + `pytest`, optional `cobc` for differential tests) | Developer |
| F7 | Low | Operations | Still no CI job for ruff + pytest. | `.github/workflows/` | Add workflow; optionally `apt-get install gnucobol` to keep the oracle active | Developer |
| F6 | Low | Supply chain | Dev deps pinned without hashes; `pip-audit` not run. | `requirements-dev.txt` | Run `pip-audit` (or `pip install --require-hashes`) in CI | Developer |
| H4 | Info | Testing | Differential sessions use a fixed seed (60 sessions); untested long sequences (e.g. many overflows) rely on unit tests. | `test_session_differential.py` | Acceptable; raise `_SESSION_COUNT` or add a nightly larger seed range if CI time allows | Developer |

Review 1 findings F1–F5, F8, F9 are verified fixed (see Remediation Status at the end).

## Security Review

- No authentication, authorization, secrets, network, files, or database; balance is synthetic and in memory (D5).
- Input handling is total and bounded: parsers never raise (`never raises` tests incl. lone surrogates), lines are read in 64-character chunks and the remainder discarded (5,000-character test), no `eval`, `float`, shell, or dynamic code.
- `fit_balance` rejects negative values (fails closed) instead of masking them.
- Test harness uses `subprocess.run` with argument lists, timeouts, and `check=True`; legacy binary built only from repository sources into a pytest temp dir.
- No OWASP CRITICAL or IMPORTANT patterns in changed code. H2 (stack traces on abnormal exit) is the only information-exposure item, local only.

## Behavior Drift Review

- Equivalent to legacy (after D2 normalization) for all recorded sessions (12), generated sessions (60), menu probes (15), recorded amount cases in `test_numeric*.py` plus 250 seeded strings, and 18,000 ad-hoc fuzz inputs.
- Intentional changes verified by tests: D2/C1 unpadded amounts (`test_format_amount`, session tests); D8/C2 EOF at menu prints goodbye and exits 0 (`test_end_of_input_at_menu_says_goodbye`).
- EOF while an amount is requested reads 0.00 like legacy (`test_end_of_input_at_amount_reads_zero_then_goodbye`).
- Drift found: H1 only (non-UTF-8 stdin encoding).

## Testing Review

- Meaningful assertions: exact full transcripts (menu, prompts with trailing space, messages), exact `Decimal` values, store state after each operation, exit codes; differential tests compare against the real legacy process. No mocks of the unit under test; `main()` exercised both in-process and as a real subprocess.
- Legacy behavior coverage: every RULE-001…018 has at least one direct test and appears in a differential session; RULE-014 also covered by fuzzing. Gaps: H1 (encoding) and H2 (abnormal termination) have no tests.

## Error Handling and Observability

- Error handling: invalid input follows legacy semantics (no errors by design); negative balance raises `ValueError` (unreachable); abnormal I/O termination not handled (H2).
- Logs: none by design — stdout is the business contract (DESIGN).
- Metrics: not applicable (local console).
- Traces: not applicable.

## Operational Readiness

- Configuration: none at runtime; dev tooling in `modernized/` (`requirements-dev.txt`, `ruff.toml`, `pytest.ini`), `.venv/` git-ignored.
- Deployment: `python modernized/account_system.py` on Python 3.10, standard library only.
- Runbooks: missing (H3).
- Rollback: legacy `src/cobol` unchanged and builds with `cobc -x`; no data migration (D5).

## Blockers

- None for functional equivalence under UTF-8/C locales.
- Before cutover (phase 4): fix H1 and add run instructions (H3). H2, F6, F7 recommended but not blocking.

## Remediation Status — Review 2 (modernize-transform, 2026-10-20)

| Finding | Status | Evidence |
| --- | --- | --- |
| H1 | Fixed | `main()` reconfigures stdin to UTF-8 + `surrogateescape`; `PYTHONIOENCODING=latin-1` with `\xe91234567` → 235567.00 = legacy; in-process and subprocess tests |
| H2 | Fixed | Ctrl+C → exit 130, broken pipe → exit 141 with empty stderr, closed stdin → goodbye + exit 0 (D8); 3 tests |
| H3 | Fixed | "Python version of the account system" section in `README.md` (run, test, differential prerequisites, approved differences, rollback) |
| F6, F7, H4 | Open | Not in transform scope |

---

# Review 1 — phases 0–1 (historical)

## Scope (Review 1)

- Target: `modernized/` — `account_system.py` (numeric semantics, DESIGN phases 0–1), `tests/`, `pytest.ini`, `ruff.toml`, `requirements-dev.txt`.
- Reviewed artifacts: [BRIEF.md](BRIEF.md) (D1–D8), [ASSESSMENT.md](ASSESSMENT.md), [RULES.md](RULES.md), [MAP.md](MAP.md), [DESIGN.md](DESIGN.md); legacy `src/cobol/*.cob` as oracle (GnuCOBOL 3.1.2, binary compiled to `/tmp`).
- Not in scope (not yet implemented): DESIGN phases 2–4 (`BalanceStore`, operations, `run()`, entry point).

## Validation Commands

Run from `modernized/` with `.venv` (Python 3.10.12).

| Command | Result | Notes |
| --- | --- | --- |
| `../.venv/bin/pytest -q --cov=account_system --cov-branch --cov-report=term-missing` | 405 passed; 100% lines (48/48), 100% branches (18/18) | Includes 331 differential cases vs compiled legacy |
| `PATH=/usr/local/sbin:/sbin ../.venv/bin/pytest -q -rs` | 74 passed, 331 skipped | Simulates an environment without `cobc`: differential suite skips with a clear reason, unit tests still run |
| `../.venv/bin/ruff check .` | All checks passed | Rules E, F, W, I, B, UP, S, SIM, PT (SIM300 ignored) |
| `../.venv/bin/ruff format --check .` | 4 files already formatted | |
| `../.venv/bin/python -m compileall -q account_system.py` | OK | |
| `../.venv/bin/python account_system.py` | rc 0, **no output** | No entry point yet (phase 3) |
| `../.venv/bin/pip-audit --version` | Not installed | Dependency audit not run; not installed by policy |
| `python3 /tmp/fuzz_amount.py <seed>` (seeds 7, 11, 23, 99) | 0 mismatches / 12,000 | Ad-hoc fuzz (from transform), alphabet `0-9+-., a*` |
| `python3 /tmp/probe_harden.py` | 7 drifts found | Input classes outside the fuzz alphabet — see F2, F3 |
| `git diff --stat -- src/cobol` | Empty | Legacy untouched |

## Ranked Findings

| Rank | Severity | Area | Finding | Evidence | Recommendation | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | High | Operational readiness | Application is not runnable: no `BalanceStore`, operations, `run()`, or `__main__` entry point. RULE-001…004, 006…009, 011…013, 015, 016, 018 have no implementation or tests. | `python account_system.py` → rc 0, no output; DESIGN phases 2–3 pending | Complete phases 2–3 via `modernize-transform` before any cutover (phase 4); re-run harden afterwards | Developer |
| 2 | Medium | Behavior drift (RULE-014) | Tab and CR are ignored by GnuCOBOL like spaces; Python returns 0.00. | Legacy vs Python: `"\t5"` 1005.00 vs 1000.00; `"1\t2"` 1012.00 vs 1000.00; `"12\r34"` 2234.00 vs 1000.00; `"5\r"` 1005.00 vs 1000.00 | Treat `\t` and `\r` like spaces in `parse_amount` (and strip `\r\n` at read time per DESIGN); add cases to unit + differential suites; amend RULE-014 step 4 | Developer |
| 3 | Medium | Behavior drift (RULE-014) | Legacy 8-position window counts **bytes**, Python counts characters; non-ASCII input diverges. | `"é1234567"` (9 bytes): legacy 1000.00, Python 235567.00 | Apply the window to the UTF-8 encoded line (or treat any non-ASCII character as invalid before windowing); add non-ASCII cases to the differential corpus; record encoding assumption (UTF-8 terminal) in DESIGN | Developer |
| 4 | Medium | Testing | Differential corpus alphabet (`0-9+-., a`) misses whitespace variants, non-ASCII, and control characters — the reason F2/F3 were not caught. | `_CORPUS_ALPHABET` in `tests/test_numeric_differential.py` | Extend alphabet with `\t`, `\r`, `é`, `*`, `b`; keep seed fixed; byte-safe subprocess I/O (`input=bytes`) | Developer |
| 5 | Medium | Security / availability (design) | DESIGN reads input with `inp.readline()` (unbounded). Very long lines would be fully buffered although only 8 (amount) or 1 (menu) characters matter. | DESIGN.md Console I/O contract | In phase 3, read with a bounded size and discard the remainder of the line; add a test with a very long line | Developer |
| 6 | Low | Supply chain | Dev dependencies pinned by version but not by hash; no audit tool run. | `requirements-dev.txt`; `pip-audit` not installed | Optionally add `--require-hashes` lock and run `pip-audit` in CI | Developer |
| 7 | Low | Operations | No CI workflow runs the Python suite; differential tests need `cobc`, which CI may lack. | `.github/workflows/` contains only workshop workflows | Add a CI job running ruff + pytest; optionally install `gnucobol` to keep the oracle active | Developer |
| 8 | Low | Code robustness | `fit_balance` applies `abs()`, silently turning a negative value positive; negative values are unreachable by design (RULE-011, unsigned parser), so a future bug would be masked. | `account_system.py` `fit_balance` | Drop `abs()` or assert non-negative input in phase 2 when callers exist | Developer |
| 9 | Info | Testing hygiene | Duplicate case `"1 2"` in `RULE_014_CASES`. | `tests/test_numeric_differential.py` | Remove duplicate | Developer |

## Security Review

- No authentication, secrets, network, file, or database surface; nothing to protect beyond correctness (BRIEF, ASSESSMENT).
- Parsers are total functions over arbitrary strings: no `eval`, `float`, regex backtracking, or exceptions; bounded to the first 8/1 characters (verified by tests and 12,000 fuzz inputs).
- Test harness runs the legacy binary with `subprocess.run([...])` (no shell), fixed arguments, 5 s timeout, `check=True`; binary is built into a pytest temp dir from repository sources only.
- Open: F5 (unbounded line read, design-level), F6 (dependency audit not run).
- No OWASP CRITICAL patterns found in changed code.

## Behavior Drift Review

- Covered and equivalent: RULE-005 (15 differential cases), RULE-010 and RULE-014 (77 direct + 316 differential cases, 12,000 ad-hoc fuzz inputs), RULE-017 with approved change D2.
- Drift found: F2 (tab/CR as whitespace), F3 (byte vs character window). Both affect only unusual input but violate D3 ("mimic GnuCOBOL").
- Menu input `"1\r"` → legacy option 1, Python `parse_choice` → 1: equivalent; `"\t1"`, `"é"`, full-width `"１"` → invalid in both.
- Not yet verifiable: full session transcripts (RULE-003, 006, 007), D8 EOF behavior — require phase 3.

## Testing Review

- Meaningful assertions: yes. Tests assert exact `Decimal` values and choices taken from RULES evidence; differential tests compare against the real legacy binary rather than snapshots; no tautological or mock-only tests. 100% line and branch coverage.
- Legacy behavior coverage: numeric rules only. Missing: store/operations (RULE-001, 002, 008…013, 015, 016), menu loop and messages (RULE-003, 004, 006, 007), EOF (RULE-018/D8), differential session transcripts with D2 normalization.

## Error Handling and Observability

- Error handling: parsing never raises by design (invalid → 0.00 / `None`), matching legacy. No other error paths exist yet.
- Logs: none (stdout is the business contract; DESIGN).
- Metrics: not applicable.
- Traces: not applicable.

## Operational Readiness

- Configuration: none required; dev tooling in `modernized/requirements-dev.txt`, `ruff.toml`, `pytest.ini`; `.venv/` ignored by git.
- Deployment: not ready — no entry point (F1).
- Runbooks: none; run/test instructions to be added at phase 4.
- Rollback: trivial — legacy `src/cobol` unchanged and still compiles with `cobc`; no data to migrate (D5).

## Blockers

- Release/cutover blocked by F1 until DESIGN phases 2–3 are implemented and this review is repeated.
- F2 and F3 should be fixed before phase 3 is closed, since they break D3 equivalence.

## Remediation Status (modernize-transform, phases 2–3, 2026-10-20)

| Finding | Status | Evidence |
| --- | --- | --- |
| F1 | Implemented, awaiting re-review | `BalanceStore`, `view_balance`, `credit`, `debit`, `run`, `main`; 538 tests pass |
| F2 | Fixed | Blanks `\t \v \f \r` ignored; unit + differential cases |
| F3 | Fixed | Window computed on UTF-8 bytes; stdin uses `surrogateescape` |
| F4 | Fixed | Corpus alphabet adds `b * \t \r \v é`; 60 generated whole-session differential cases |
| F5 | Fixed | `_read_line` reads 64-char chunks and discards the rest; 5,000-char line test |
| F8 | Fixed | `fit_balance` raises `ValueError` on negative input |
| F9 | Fixed | Duplicate case removed |
| F6, F7 | Open | Not in transform scope |

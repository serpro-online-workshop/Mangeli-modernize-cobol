# Modernization Assessment — account-system

Input: [BRIEF.md](BRIEF.md) (decisions D1–D7). Legacy evidence: `src/cobol/` (read-only).

## Executive Summary

- Modernization pattern: **full replacement (rewrite) of a single small module**, validated by golden-master differential tests against the compiled GnuCOBOL binary (D1). Strangler/incremental coexistence is unnecessary: 99 lines, one executable, no integrations.
- Major findings:
  1. Tiny, self-contained 3-program console app; three-layer structure (UI → rules → storage) maps cleanly to Python functions/classes.
  2. Legacy runtime exposes several **non-obvious behaviors** that must be reproduced under D3/D4: sign dropped on negative input, extra decimals truncated, multi-digit menu input truncated to first digit, non-numeric amount treated as 0, high-order truncation on overflow, and an anomaly when accepting `999999.99`.
  3. **Infinite loop on EOF**: if stdin closes before option 4, the menu loops forever (6.5M output lines in 3 s).
  4. No tests, no build script, no CI for the application; no Python code yet.
- Blockers: none. Two behaviors need a decision or deeper characterization (see R3, R7).

## Inventory

| Area | Evidence | Notes |
| --- | --- | --- |
| Languages | COBOL: `src/cobol/main.cob` (36 lines), `operations.cob` (40), `data.cob` (23) — 99 total (`wc -l`) | No copybooks, JCL, SQL, or other languages in app scope |
| Build system | Manual `cobc -x src/cobol/main.cob src/cobol/operations.cob src/cobol/data.cob -o accountsystem` (`.github/prompts/runCobolApp.prompt.md`) | No Makefile/script; GnuCOBOL 3.1.2.0; `cobc -fsyntax-only -Wall` → rc 0, no warnings |
| Dependencies | GnuCOBOL runtime only | No third-party libraries |
| Tests | None for the app | `.github/workflows/3-create-test-plan.yml` and `.github/steps/3-create-test-plan.md` are workshop guidance, not tests |
| Data stores | `STORAGE-BALANCE PIC 9(6)V99 VALUE 1000.00` in `data.cob` WORKING-STORAGE | In-memory, lost at exit (D5) |
| Integrations | None | Static `CALL` between the 3 programs only |
| Runtime entry points | `MainProgram` (`main.cob`, `PROCEDURE DIVISION` → `MAIN-LOGIC`) | Interactive stdin/stdout; subprograms `Operations`, `DataProgram` |

Architecture diagram: [ARCHITECTURE.mmd](ARCHITECTURE.mmd).

## Observed Runtime Behavior (legacy oracle, GnuCOBOL 3.1.2)

Inputs piped to `/tmp/accountsystem`; output filtered to result lines. These are **observations**, not yet rule cards.

| Input sequence | Observed output | Note |
| --- | --- | --- |
| `1`,`4` | `Current balance: 001000.00` | Initial balance |
| `2`,`500` | `Amount credited. New balance: 001500.00` | Normal credit |
| `3`,`1000` | `Amount debited. New balance: 000000.00` | Debit equal to balance allowed (`>=`) |
| `3`,`2000` | `Insufficient funds for this debit.` | Rejection |
| `2`,`-50` | `New balance: 001050.00` | Sign dropped (unsigned `PIC 9`) |
| `2`,`12.345` | `New balance: 001012.34` | Extra decimals truncated, not rounded |
| `2`,`abc` | `New balance: 001000.00` | Non-numeric → 0 |
| `2`,`1234567` | `New balance: 235567.00` | Integer part keeps low-order 6 digits |
| `2`,`999000` | `New balance: 000000.00` | 1000000.00 → high-order truncation |
| `2`,`99999.99` | `New balance: 100999.99` | Normal |
| `2`,`999999.99` | `New balance: 000999.90` | **Anomaly**: expected `000999.99`; last decimal lost on ACCEPT of 9-char input |
| `2`,`0.01` | `New balance: 001000.01` | Smallest amount |
| `9`,`4` / `x`,`4` / empty,`4` | `Invalid choice, please select 1-4.` | Invalid menu |
| `12`,`4` | `Current balance: 001000.00` | Multi-digit menu → first digit |
| `1` then EOF | Infinite menu loop (timeout rc 124) | No EOF handling |

## Complexity and Risk

| ID | Finding | Category | Severity | Evidence | Recommendation |
| --- | --- | --- | --- | --- | --- |
| R1 | GnuCOBOL `ACCEPT` numeric parsing (sign drop, decimal truncation, non-numeric → 0, digit truncation) | Behavior fidelity | High | Runtime table above; `AMOUNT PIC 9(6)V99` (`operations.cob` L7) | Extract as explicit rules; implement a dedicated parser; golden-master tests per case |
| R2 | Overflow truncation on `ADD` without `ON SIZE ERROR` | Behavior fidelity | Medium | `operations.cob` L24; `999000` → `000000.00` | Implement modulo 1,000,000 on integer part (D4); boundary tests |
| R3 | `999999.99` ACCEPT anomaly (→ `999999.90`) | Behavior fidelity | Medium | Runtime table | Explained in RULES.md RULE-014: ACCEPT keeps only the first 8 input characters |
| R4 | Menu `PIC 9` takes first character only | Behavior fidelity | Medium | `main.cob` L6, `12` → option 1 | Rule card + tests (D3 preserve) |
| R5 | Infinite loop on EOF | Reliability / DoS | Medium | `printf '1\n' \| timeout 3 ./accountsystem` → 6,588,721 lines, rc 124 | Decide in reimagine: preserve (not useful) or exit on EOF as intentional change |
| R6 | Literal `'READ'`/`'WRITE'` (4/5 bytes) passed to `PIC X(6)` linkage | Latent defect | Low | `operations.cob` L17, L23, L25; `data.cob` L10 | Works in GnuCOBOL; irrelevant in Python (use enum/methods) |
| R7 | Nested `IF/ELSE IF` with single `END-IF`; `GOBACK` only in innermost else-branch | Readability | Low | `operations.cob` L16–40, `data.cob` L16–23 | Implicit return makes it work; map to explicit dispatch |
| R8 | Unused initial `FINAL-BALANCE VALUE 1000.00` in Operations | Dead code | Low | `operations.cob` L8 | Do not replicate |
| R9 | Display format `001000.00` vs approved `1000.00` | Intentional change | Low | D2 | Normalize amount field in differential tests |
| R10 | No tests or build automation | Test gap | High | Inventory | Golden-master harness invoking `cobc` binary + pytest suite |

## Security and Compliance Notes

- No authentication, authorization, network, file, or database surface; single local user.
- No sensitive data; balance is synthetic (BRIEF).
- Input is unvalidated by design (D3); in Python, parsing must not use `eval`/`float` and must be bounded to avoid crashes on arbitrary strings.
- EOF infinite loop (R5) is the only availability concern; relevant if the program is ever run non-interactively.
- A dedicated `se-security-reviewer` pass is not warranted at this risk level; revisit in `modernize-harden`.

## Documentation Gaps

- No functional specification or rule catalog (to be produced by `modernize-extract-rules`).
- No documented build/run instructions outside the workshop prompt.
- Numeric input semantics are undocumented and compiler-dependent (GnuCOBOL 3.1.2 default dialect).
- Test plan referenced by workshop (`docs/TESTPLAN.md`) does not exist in the repository.

## Modernization Recommendations

- Rewrite as one plain Python 3.10 module (D6) under `modernized/`, preserving the three-layer separation as functions/classes (UI, operations, storage).
- Use `decimal.Decimal` with explicit truncation (`ROUND_DOWN`) and modulo for `PIC 9(6)V99` semantics.
- Build a golden-master harness first: compile legacy with `cobc` to a temp path, replay input scripts, compare transcripts with amount-format normalization (R9).
- Characterize R1–R5 cases before implementation; settle R3 and R5 as preserve vs. intentional change.

## Commands Run

| Command | Result | Notes |
| --- | --- | --- |
| `which scc cloc` | Not found | Tools unavailable; not installed by policy |
| `wc -l src/cobol/*.cob` | 23 / 36 / 40 = 99 | Line counts |
| `find . -type f ( *.cpy, *.jcl, Makefile, *.py, package.json, *test* )` | Only workshop files | No copybooks, build, or tests |
| `cobc --version` | GnuCOBOL 3.1.2.0 | |
| `cobc -fsyntax-only -Wall src/cobol/*.cob` | rc 0, no warnings | |
| `cobc -x ... -o /tmp/accountsystem` | Success | Binary outside repo |
| Piped input probes (table above) | rc 0 each | Observed behavior |
| `printf '1\n' \| timeout 3 /tmp/accountsystem \| wc -l` | 6,588,721 lines, rc 124 | EOF infinite loop |
| `git log --oneline` | 3 commits | No application history |

## Diagram Artifacts

- [`analysis/account-system/ARCHITECTURE.mmd`](ARCHITECTURE.mmd)

## Next Handoff

- `modernize-extract-rules`: turn the observed runtime table and source logic into cited rule cards (`RULES.md`); characterize R3 (inputs ≥ 9 chars).
- `modernize-map`: map MainProgram/Operations/DataProgram to Python module boundaries.
- `modernize-reimagine`: decide R5 (EOF) and confirm parser semantics.
- `modernize-transform` / `modernize-harden`: golden-master harness + pytest, ruff, coverage.

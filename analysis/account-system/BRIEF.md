# Modernization Brief — account-system (COBOL → Python 3.10)

## Scope

- In scope:
  - The three COBOL programs under `src/cobol/`: `main.cob` (MainProgram, menu/UI), `operations.cob` (Operations, balance rules), `data.cob` (DataProgram, in-memory balance storage).
  - Behavior-preserving rewrite to Python 3.10 under `modernized/`, with characterization tests (`pytest`) and lint (`ruff`).
  - Analysis artifacts under `analysis/account-system/`.
- Out of scope:
  - Editing `src/cobol/**` (read-only legacy evidence).
  - Multi-account support, customers, transaction history, audit trail (absent in the legacy system).
  - Web/API, database, deployment infrastructure (not decided; see Open Questions).
  - The workshop's original Node.js target (`.github/steps/4-convert-the-app.md`); replaced by Python per user decision.

## Business Drivers

- Driver (assumption): retire COBOL as part of a GitHub Copilot modernization workshop (`README.md`, `.github/steps/`), using Python as the target language (user decision).
- Expected value (assumption): code maintainable by teams without COBOL skills, with automated tests that pin legacy behavior; learning a disciplined, evidence-driven modernization workflow.

## Stakeholders

| Role | Name or group | Decision area | Open question |
| --- | --- | --- | --- |
| Initiative owner / developer | Workshop participant (repo owner) | Scope, target stack, intentional changes | Confirm behavior changes listed under Assumptions |
| Business owner | Same as initiative owner (D7) | Meaning of balance rules and limits | — |
| Technical reviewer | Same as initiative owner (D7) | Code review, acceptance of tests | — |

## Constraints and Non-Goals

### Constraints

- Runtime: Python 3.10 (3.10.12 observed locally); standard library only unless approved; money as `decimal.Decimal` with 2 decimal places (`.github/copilot-instructions.md`).
- Legacy runtime: GnuCOBOL 3.1.2.0 at `/usr/bin/cobc` (installed manually by the owner); compile command in `.github/prompts/runCobolApp.prompt.md`. Verified: compiled binary runs and prints `Current balance: 001000.00` for option 1.
- Interface: interactive console (stdin/stdout), menu options 1–4 and messages from `src/cobol/main.cob`.
- Numeric domain: balance and amount `PIC 9(6)V99` — 0 to 999999.99, unsigned (`src/cobol/operations.cob`, `src/cobol/data.cob`).
- Compliance: none identified; unknown.
- Data sensitivity: no personal or real financial data; a single synthetic balance held in memory (initial 1000.00). Test data must remain synthetic.
- Timeline: none (self-paced workshop, D7).

### Non-Goals

- Adding persistence, authentication, or multi-account features in the first slice.
- Fixing legacy quirks silently; any deviation must be recorded as an intentional change before implementation.
- Performance or scalability work (single-user console program).

## Risks

| Risk | Impact | Likelihood | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Oracle drift between GnuCOBOL runs and Python | Characterization tests may pin wrong behavior | Low | GnuCOBOL installed; capture golden-master transcripts from the compiled legacy binary | Developer |
| Implicit compiler-dependent behavior (literal `'READ'`/`'WRITE'` passed to `PIC X(6)` linkage; nested `IF/ELSE IF` with single `END-IF`) | Python may diverge in edge cases | Medium | Pin via rule extraction + tests; record decisions | Developer |
| Unvalidated input (`ACCEPT` into `PIC 9` / `PIC 9(6)V99`) | Odd results for non-numeric, negative or multi-digit input | High | Decision D3: preserve legacy behavior; pin exact GnuCOBOL results with golden-master tests | Initiative owner |
| Silent truncation on credit overflow (`ADD` without `ON SIZE ERROR`) | Balance wraps/truncates above 999999.99 | Medium | Decision D4: reproduce COBOL truncation; pin boundary tests | Initiative owner |
| Float usage in Python | Rounding errors on money | Medium | Enforce `Decimal`; lint/test rule | Developer |
| Balance not persisted (resets each run) | Users may expect persistence in the new version | Low | Decision D5: no persistence | Initiative owner |
| Display format change (D2) breaks byte-for-byte transcript comparison | Differential tests fail on balance lines | Medium | Normalize balance format in differential tests; document as intentional change | Developer |

## Success Criteria

- Python 3.10 module under `modernized/` reproduces menu, messages, initial balance, credit, debit, insufficient-funds, input-handling and overflow behavior of `src/cobol/`, with amounts shown as `1000.00` (D2).
- Characterization tests cover every extracted rule (view, credit, debit success, debit rejection, boundaries, invalid menu option, exit) and pass with `pytest`.
- Line coverage of the Python package at 100% (`pytest-cov`); `ruff check` clean.
- No `float` in money paths; all intentional changes documented in `analysis/account-system/` with approval.
- Legacy `src/cobol/**` unchanged.

## Assumptions

- The goal is a functional equivalent console app, not a redesign (derived from workshop step 4 wording "functionally equivalent", adapted to Python).
- Single account and in-memory state are acceptable for the first release.
- Exact console text (including spacing) must be preserved, except balance formatting (D2).
- No external systems, files, batch jobs, or databases interact with this program (no JCL, copybooks, or file I/O found in `src/cobol/`).

## Decisions

Approved by the initiative owner on 2026-10-20.

| ID | Decision | Type | Impact |
| --- | --- | --- | --- |
| D1 | Use the compiled GnuCOBOL 3.1.2 binary as the runtime oracle (golden-master transcripts). | Technical | Characterization tests compare against real legacy output |
| D2 | Display amounts as `1000.00` instead of COBOL `001000.00` (no zero padding, 2 decimals). | **Intentional change** | All balance messages; differential tests normalize this field |
| D3 | Keep current input behavior (no extra validation); mimic GnuCOBOL handling of non-numeric, negative, multi-digit and >2-decimal input. | Preserve | Input parsing must be characterized case by case |
| D4 | Credit overflow above 999999.99 truncates like COBOL (high-order digits dropped). | Preserve | Credit rule and boundary tests |
| D5 | No persistence; balance resets to 1000.00 each run. | Preserve | In-memory storage only |
| D6 | Packaging: plain module (no `pyproject.toml` package). | Technical | Layout under `modernized/` |
| D7 | No timeline or approval gate beyond the workshop. | Process | Owner self-approves stages |
| D8 | On end of input at the menu, print `Exiting the program. Goodbye!` and exit with code 0 instead of looping forever (RULE-018, DESIGN C2). | **Intentional change** | Menu loop EOF handling; session test |

## Open Questions

| Question | Owner | Needed by | Blocks |
| --- | --- | --- | --- |
| None open. Edge-case behaviors under D3/D4 will be measured in modernize-assess / extract-rules. | — | — | — |

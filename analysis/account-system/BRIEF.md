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
| Business owner | Unknown | Meaning of balance rules and limits | Does one exist beyond the workshop? |
| Technical reviewer | Unknown | Code review, acceptance of tests | Who approves the transform? |

## Constraints and Non-Goals

### Constraints

- Runtime: Python 3.10 (3.10.12 observed locally); standard library only unless approved; money as `decimal.Decimal` with 2 decimal places (`.github/copilot-instructions.md`).
- Legacy runtime: GnuCOBOL `cobc` (compile command in `.github/prompts/runCobolApp.prompt.md`); **not installed** in the current environment (`which cobc` returned nothing).
- Interface: interactive console (stdin/stdout), menu options 1–4 and messages from `src/cobol/main.cob`.
- Numeric domain: balance and amount `PIC 9(6)V99` — 0 to 999999.99, unsigned (`src/cobol/operations.cob`, `src/cobol/data.cob`).
- Compliance: none identified; unknown.
- Data sensitivity: no personal or real financial data; a single synthetic balance held in memory (initial 1000.00). Test data must remain synthetic.
- Timeline: unknown (self-paced workshop).

### Non-Goals

- Adding persistence, authentication, or multi-account features in the first slice.
- Fixing legacy quirks silently; any deviation must be recorded as an intentional change before implementation.
- Performance or scalability work (single-user console program).

## Risks

| Risk | Impact | Likelihood | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| No live COBOL oracle (`cobc` missing) | Characterization tests based only on reading code may misstate behavior | High | Install GnuCOBOL and capture golden-master transcripts, or explicitly accept code-reading oracle | Developer |
| Implicit compiler-dependent behavior (literal `'READ'`/`'WRITE'` passed to `PIC X(6)` linkage; nested `IF/ELSE IF` with single `END-IF`) | Python may diverge in edge cases | Medium | Pin via rule extraction + tests; record decisions | Developer |
| Unvalidated input (`ACCEPT` into `PIC 9` / `PIC 9(6)V99`) | Undefined/odd results for non-numeric, negative or multi-digit input | High | Decide preserve vs. validate as intentional change in DESIGN | Initiative owner |
| Silent truncation on credit overflow (`ADD` without `ON SIZE ERROR`) | Balance corruption above 999999.99 | Medium | Decide preserve vs. reject; test both boundaries | Initiative owner |
| Float usage in Python | Rounding errors on money | Medium | Enforce `Decimal`; lint/test rule | Developer |
| Balance not persisted (resets each run) | Users may expect persistence in the new version | Low | Keep as non-goal unless approved | Initiative owner |

## Success Criteria

- Python 3.10 application under `modernized/` reproduces menu, messages, initial balance, credit, debit, and insufficient-funds behavior of `src/cobol/`.
- Characterization tests cover every extracted rule (view, credit, debit success, debit rejection, boundaries, invalid menu option, exit) and pass with `pytest`.
- Line coverage of the Python package at 100% (`pytest-cov`); `ruff check` clean.
- No `float` in money paths; all intentional changes documented in `analysis/account-system/` with approval.
- Legacy `src/cobol/**` unchanged.

## Assumptions

- The goal is a functional equivalent console app, not a redesign (derived from workshop step 4 wording "functionally equivalent", adapted to Python).
- Single account and in-memory state are acceptable for the first release.
- Exact console text (including spacing and the COBOL numeric display format, e.g. `001000.00`) must be preserved unless an intentional change is approved — to be confirmed.
- No external systems, files, batch jobs, or databases interact with this program (no JCL, copybooks, or file I/O found in `src/cobol/`).

## Open Questions

| Question | Owner | Needed by | Blocks |
| --- | --- | --- | --- |
| Install GnuCOBOL to generate a runtime oracle, or accept code-reading as oracle? | Developer (technical) | modernize-assess | Characterization test strategy |
| Preserve COBOL numeric display format (`001000.00`) or show `1000.00`? | Initiative owner (business) | modernize-reimagine | Output contract, tests |
| Validate input (non-numeric, negative, >2 decimals, multi-digit menu) or mimic legacy? | Initiative owner (business) | modernize-reimagine | Input handling design |
| On credit overflow above 999999.99: truncate like legacy or reject? | Initiative owner (business) | modernize-reimagine | Credit rule |
| Should balance persist between runs? | Initiative owner (business) | modernize-reimagine | Data/storage design |
| Packaging: plain module, installable package (`pyproject.toml`), or both? | Developer (technical) | modernize-map | Project layout |
| Any timeline or review/approval gate beyond the workshop? | Initiative owner | modernize-map | Sequencing |

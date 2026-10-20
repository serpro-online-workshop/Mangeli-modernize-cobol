# Repository instructions

Modernization of the COBOL account management system (`src/cobol/`) to Python.

## Zones

| Zone | Contract |
| --- | --- |
| `src/cobol/**` | Legacy evidence (equivalent to `legacy/**`). Read-only unless explicitly requested. |
| `analysis/account-system/**` | BRIEF, ASSESSMENT, RULES, MAP, DESIGN and validation evidence. |
| `modernized/**` | Python implementation (package + `tests/`). |

## Target stack

- Python 3.10 (do not use 3.11+ features such as `tomllib`, `ExceptionGroup`, `typing.Self`), standard library only unless a dependency is approved.
- Money values use `decimal.Decimal` with 2 decimal places; never `float`.
- Tests with `pytest` (+ `pytest-cov`); lint/format with `ruff`.

## Behavior to preserve

- Initial balance 1000.00; range 0 to 999999.99 (`PIC 9(6)V99`).
- Debit rejected when amount exceeds balance ("Insufficient funds for this debit.").
- Menu options 1-4 and messages from `src/cobol/main.cob`.
- Input handling and credit overflow truncation mimic GnuCOBOL; no persistence.

Approved intentional change: amounts display as `1000.00` (not `001000.00`). See decisions in `analysis/account-system/BRIEF.md`.

Any deviation (input validation, overflow handling, persistence) is an intentional change and must be recorded in `analysis/account-system/` before implementation.

## Workflow

Use the `modernization` agent with the prompts in order: `/modernize-brief` → `/modernize-assess` → `/modernize-extract-rules` → `/modernize-map` → `/modernize-reimagine` → `/modernize-transform` → `/modernize-harden`.

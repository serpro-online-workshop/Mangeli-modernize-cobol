# Modernization Map — account-system

Inputs: [BRIEF.md](BRIEF.md) (D1–D7), [ASSESSMENT.md](ASSESSMENT.md), [RULES.md](RULES.md) (RULE-001 … RULE-018).

## Source Scope

- Legacy system folder: `src/cobol/` (`main.cob`, `operations.cob`, `data.cob`) — read-only evidence.
- Target architecture: one plain Python 3.10 module (D6), standard library only, console stdin/stdout, in-memory state (D5), `decimal.Decimal` for money; tests with `pytest` under `modernized/tests/`.

## Legacy Areas

| Legacy module or area | Business domain | Data stores | Integrations | Evidence |
| --- | --- | --- | --- | --- |
| `MainProgram` (`main.cob`) — menu loop, choice input, routing, exit | Presentation / interaction | `USER-CHOICE PIC 9`, `CONTINUE-FLAG` (local) | stdin/stdout; static `CALL 'Operations'` | RULE-003…007, RULE-018 |
| `Operations` (`operations.cob`) — view, credit, debit, amount input, messages | Account operations (business rules) | `AMOUNT`, `FINAL-BALANCE PIC 9(6)V99` (working copies) | stdin/stdout; static `CALL 'DataProgram'` | RULE-008…015, RULE-017 |
| `DataProgram` (`data.cob`) — READ/WRITE balance | Account state | `STORAGE-BALANCE PIC 9(6)V99 VALUE 1000.00` (in-memory) | none | RULE-001, RULE-002, RULE-016 |
| GnuCOBOL runtime semantics — `ACCEPT` into numeric fields, `ADD` truncation, numeric `DISPLAY` | Cross-cutting numeric contract | — | GnuCOBOL 3.1.2 | RULE-005, RULE-010, RULE-014, RULE-017 |
| Build (`cobc -x …`) | Tooling | — | GnuCOBOL | ASSESSMENT inventory |

No files, databases, batch jobs, or external integrations exist (ASSESSMENT).

## Target Mapping

Single module `modernized/account_system.py`; sections are logical boundaries inside that file, not separate packages (D6).

| Legacy area | Target package/service/module | Retain, replace, wrap, or retire | Rationale |
| --- | --- | --- | --- |
| GnuCOBOL numeric semantics (`PIC 9(6)V99`, `PIC 9`) | `account_system.py` — pure functions: `parse_amount(text) -> Decimal` (RULE-014), `parse_choice(text) -> int \| None` (RULE-005), `format_amount(Decimal) -> str` (RULE-017, D2), `fit_pic_9_6v99(Decimal) -> Decimal` (RULE-010) | Replace | Isolates compiler-dependent behavior so it can be pinned by focused unit tests |
| `DataProgram` | `account_system.py` — `BalanceStore` (in-memory, initial `Decimal("1000.00")`, `read()`/`write()`) | Replace | 1:1 with READ/WRITE; keeps the storage seam if persistence is ever approved |
| `Operations` | `account_system.py` — `view_balance`, `credit`, `debit` functions taking store + I/O | Replace | Holds RULE-008…013, RULE-015; messages kept verbatim |
| `MainProgram` | `account_system.py` — `run(stdin, stdout)` menu loop + `if __name__ == "__main__"` entry | Replace | RULE-003…007; injectable streams for tests; EOF policy from reimagine (RULE-018) |
| Literal `'READ'`/`'WRITE'` vs `PIC X(6)`, `GOBACK` placement, unused `FINAL-BALANCE` initial value | — | Retire | Implementation artifacts without observable behavior (RULES Cross-Rule Notes; ASSESSMENT R6–R8) |
| `src/cobol/**` + `cobc` binary | Kept as differential oracle | Retain (as oracle) | D1; compared via golden-master tests, not deployed |
| Manual `cobc` build | `python modernized/account_system.py`; tests via `pytest modernized/tests` | Replace | No packaging (D6) |

Test layout (target, `modernized/tests/`):

| Test area | Covers |
| --- | --- |
| Unit: parsing/formatting/overflow | RULE-005, RULE-010, RULE-014, RULE-017 |
| Unit: store + operations | RULE-001, RULE-002, RULE-008…013, RULE-015, RULE-016 |
| Session: scripted stdin → stdout transcript | RULE-003, RULE-004, RULE-006, RULE-007, RULE-018 |
| Differential (golden master vs compiled legacy, skipped when `cobc` absent) | All observable rules; amounts normalized for D2 |

## Data Flows

| Flow | Source | Target | Data migration checkpoint | Validation |
| --- | --- | --- | --- | --- |
| Menu choice | stdin → `USER-CHOICE PIC 9` | stdin → `parse_choice` | None (transient) | RULE-005 table cases |
| Amount | stdin → `AMOUNT PIC 9(6)V99` | stdin → `parse_amount` → `Decimal` | None (transient) | RULE-014 table cases |
| Balance read/write | `Operations` ↔ `DataProgram` via `CALL` | operations ↔ `BalanceStore` | None — no persisted data (D5); checkpoint = initial balance 1000.00 at start | RULE-001, RULE-016 |
| Output messages | `DISPLAY` → stdout | `print`/stream write → stdout | None | Differential transcript with amount normalization (RULE-017) |

No data migration is required: the legacy system holds no durable data.

## Migration Sequence

Big-bang replacement of the executable, built in internal slices. The strangler boundary is the process interface (stdin/stdout transcript): legacy and Python can be swapped per run because neither keeps state.

| Order | Slice | Strangler boundary | Entry criteria | Exit criteria | Rollback consideration |
| --- | --- | --- | --- | --- | --- |
| 0 | Golden-master harness + corpus (scripted inputs → legacy transcripts) | Process stdin/stdout | `cobc` 3.1.2 available; RULES approved | Corpus covers every RULE example; legacy transcripts captured and reproducible | Delete harness; no product impact |
| 1 | Numeric semantics (`parse_amount`, `parse_choice`, `format_amount`, overflow fit) | Pure functions | Slice 0 corpus; D2/D3/D4 | Unit tests green for RULE-005/010/014/017 examples | Revert module; legacy untouched |
| 2 | `BalanceStore` + `view_balance`/`credit`/`debit` | Function API | Slice 1 green | Unit tests green for RULE-001/002/008…013/015/016 | Revert module |
| 3 | Menu loop `run()` + entry point | Process stdin/stdout | Slice 2 green; RULE-018 decision from reimagine | Differential suite equal to legacy (after D2 normalization); ruff clean; 100% line coverage | Keep running `cobc` binary |
| 4 | Cutover: Python becomes the documented way to run the app | Run instructions | Slice 3 exit criteria; harden review | `modernize-harden` report with no open high findings | Revert docs; `src/cobol` still builds |

## Risks and Review Notes

- Pressure-test: a single module risks mixing UI and rules; mitigated by the internal function boundaries above and injectable streams. If the file grows beyond easy review, splitting is a D6 change and must be recorded first.
- Differential tests depend on a local GnuCOBOL install; they must skip, not fail, when `cobc` is missing, while unit tests stay authoritative in CI.
- RULE-018 (EOF) blocks slice 3 exit criteria until `modernize-reimagine` decides preserve vs. clean exit; the golden-master corpus must always end with `4` to avoid hanging the legacy binary.
- RULE-014 parser is runtime-derived from ~20 samples; slice 0 should extend the corpus with generated inputs before slice 1 is considered done.
- Python `Decimal` default context rounds half-even; truncation must be explicit (`ROUND_DOWN`) to match RULE-014/RULE-010.

## Diagram

- [`analysis/account-system/MAP.mmd`](MAP.mmd)

## Handoff

- To `modernize-reimagine`: confirm function contracts and module layout above, decide RULE-018 (EOF), define I/O contract (prompts without trailing newline vs. COBOL `DISPLAY` newlines), and golden-master normalization rule for D2.
- To `modernize-transform` (after design approval): slices 0 → 3 in order; slice 1 is the first transform candidate.

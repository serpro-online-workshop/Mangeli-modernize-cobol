# Business Rules — account-system

Inputs: [BRIEF.md](BRIEF.md) (decisions D1–D7), [ASSESSMENT.md](ASSESSMENT.md).
Runtime oracle: GnuCOBOL 3.1.2.0, `cobc -x src/cobol/{main,operations,data}.cob -o /tmp/accountsystem`, inputs piped via stdin (probe script `/tmp/probe_legacy.sh`, outside the repository).

## Summary

- Source scope: `src/cobol/main.cob`, `src/cobol/operations.cob`, `src/cobol/data.cob` (all reachable code; no copybooks, files, or DB).
- Rule count: 18 (RULE-001 … RULE-018).
- Low-confidence count: 0. Medium: 2 (RULE-005, RULE-018) — behavior observed at runtime but rests on GnuCOBOL runtime semantics not visible in source. RULE-014 raised to high after differential fuzzing.
- Evidence state: all **observed** (source and/or runtime). RULE-017 carries an approved intentional change (D2).
- Searched categories: calculations, validations, eligibility, authorization (none present), routing, defaults, limits, state transitions, error handling, negative paths, data integrity.

## Rule Cards

### RULE-001 — Initial balance is 1000.00

- Type: policy (default)
- Evidence state: observed
- Plain language: Each program run starts with an account balance of 1000.00.
- Source evidence:
  - `src/cobol/data.cob` L6 — `STORAGE-BALANCE PIC 9(6)V99 VALUE 1000.00`
  - `src/cobol/operations.cob` L8 — `FINAL-BALANCE ... VALUE 1000.00` (overwritten by READ before use; not authoritative)
  - Runtime: input `1`,`4` → `Current balance: 001000.00`
- Examples:
  - Given a fresh run, When the user selects `1`, Then the balance shown is 1000.00.
- Confidence: high
- Requirement candidate: yes

### RULE-002 — Balance and amount domain

- Type: other (data-integrity constraint)
- Evidence state: observed
- Plain language: Balance and transaction amount are unsigned decimals with 6 integer and 2 fractional digits: 0.00 to 999999.99.
- Source evidence:
  - `src/cobol/data.cob` L6, L11 — `PIC 9(6)V99`
  - `src/cobol/operations.cob` L7–8 — `AMOUNT`, `FINAL-BALANCE PIC 9(6)V99`
- Examples:
  - Given balance 1000.00, When crediting `99999.99`, Then balance is 100999.99.
  - Given balance 1000.00, When debiting `1000`, Then balance is 0.00 (lower bound reachable).
- Confidence: high
- Requirement candidate: yes

### RULE-003 — Menu presentation

- Type: other (UI contract)
- Evidence state: observed
- Plain language: Before each choice, the program prints, one per line: `--------------------------------`, `Account Management System`, `1. View Balance`, `2. Credit Account`, `3. Debit Account`, `4. Exit`, `--------------------------------`, `Enter your choice (1-4): `.
- Source evidence:
  - `src/cobol/main.cob` L12–19 — `DISPLAY` statements
- Examples:
  - Given program start, When nothing is entered yet, Then the 8 menu lines above are printed in order.
- Confidence: high
- Requirement candidate: yes

### RULE-004 — Menu routing

- Type: routing
- Evidence state: observed
- Plain language: Choice 1 shows the balance, 2 credits, 3 debits, 4 exits.
- Source evidence:
  - `src/cobol/main.cob` L22–30 — `EVALUATE USER-CHOICE`, `CALL 'Operations' USING 'TOTAL '|'CREDIT'|'DEBIT '`, `MOVE 'NO' TO CONTINUE-FLAG`
  - `src/cobol/operations.cob` L16, L20, L28 — dispatch on `OPERATION-TYPE`
- Examples:
  - Given the menu, When the user enters `2`, Then `Enter credit amount: ` is printed.
  - Given the menu, When the user enters `3`, Then `Enter debit amount: ` is printed.
- Confidence: high
- Requirement candidate: yes

### RULE-005 — Menu input uses only the first character

- Type: validation
- Evidence state: observed (runtime) — source shows `PIC 9` (1 position); character handling is GnuCOBOL `ACCEPT` semantics
- Plain language: Only the first character of the menu line is considered. If it is `1`–`4` the option runs; any other first character (`0`, `5`–`9`, letter, space, sign, empty line) is invalid. Remaining characters on the line are discarded.
- Source evidence:
  - `src/cobol/main.cob` L6 — `USER-CHOICE PIC 9`; L20 — `ACCEPT USER-CHOICE`
  - Runtime: `12`→ option 1; `1x` → option 1; `3a` → option 3; `0`, `5`, `9`, `x`, ` 1`, `-1`, `+1`, empty → `Invalid choice, please select 1-4.`
- Examples:
  - Given the menu, When the user enters `12`, Then `Current balance: ...` is shown (option 1).
  - Given the menu, When the user enters ` 1` (leading space), Then `Invalid choice, please select 1-4.` is shown.
- Confidence: medium (runtime-specific; confirm on the same GnuCOBOL version used for golden masters)
- Requirement candidate: yes (D3 preserve)

### RULE-006 — Invalid choice keeps the loop running

- Type: validation / error handling
- Evidence state: observed
- Plain language: An invalid choice prints `Invalid choice, please select 1-4.` and the menu is shown again; balance unchanged.
- Source evidence:
  - `src/cobol/main.cob` L31–32 — `WHEN OTHER DISPLAY "Invalid choice, please select 1-4."`; L11 — `PERFORM UNTIL CONTINUE-FLAG = 'NO'`
- Examples:
  - Given balance 1000.00, When the user enters `9` then `1`, Then the invalid message appears, then `Current balance: 001000.00`.
- Confidence: high
- Requirement candidate: yes

### RULE-007 — Exit

- Type: state-transition
- Evidence state: observed
- Plain language: Choice 4 ends the loop, prints `Exiting the program. Goodbye!`, and terminates with exit code 0.
- Source evidence:
  - `src/cobol/main.cob` L29–30, L35–36 — `MOVE 'NO' TO CONTINUE-FLAG`, `DISPLAY "Exiting the program. Goodbye!"`, `STOP RUN`
  - Runtime: input `4` → last line `Exiting the program. Goodbye!`, rc 0
- Examples:
  - Given the menu, When the user enters `4`, Then `Exiting the program. Goodbye!` is printed and the program ends.
- Confidence: high
- Requirement candidate: yes

### RULE-008 — View balance

- Type: other (query)
- Evidence state: observed
- Plain language: Option 1 reads the stored balance and prints `Current balance: <amount>` without changing it.
- Source evidence:
  - `src/cobol/operations.cob` L16–18 — `CALL 'DataProgram' USING 'READ'`, `DISPLAY "Current balance: " FINAL-BALANCE`
  - `src/cobol/data.cob` L16–17 — `MOVE STORAGE-BALANCE TO BALANCE`
- Examples:
  - Given balance 1050.00, When the user selects `1`, Then `Current balance: 001050.00` (legacy) / `Current balance: 1050.00` (target, D2).
- Confidence: high
- Requirement candidate: yes

### RULE-009 — Credit adds the amount

- Type: calculation
- Evidence state: observed
- Plain language: Option 2 prompts `Enter credit amount: `, reads the amount, adds it to the stored balance, stores the result, and prints `Amount credited. New balance: <amount>`. No eligibility check.
- Source evidence:
  - `src/cobol/operations.cob` L20–26 — `ACCEPT AMOUNT`, `ADD AMOUNT TO FINAL-BALANCE`, `CALL 'DataProgram' USING 'WRITE'`, `DISPLAY "Amount credited. New balance: "`
  - `src/cobol/data.cob` L19–20 — `MOVE BALANCE TO STORAGE-BALANCE`
- Examples:
  - Given balance 1000.00, When crediting `500`, Then `Amount credited. New balance: 001500.00`.
  - Given balance 1000.00, When crediting `0`, Then balance stays 1000.00 and the credited message is still shown.
- Confidence: high
- Requirement candidate: yes

### RULE-010 — Credit overflow truncates high-order digits

- Type: calculation (limit)
- Evidence state: observed
- Plain language: If balance + amount ≥ 1,000,000.00, the integer part keeps only its low-order 6 digits (result = sum mod 1,000,000.00). No error message; the credited message is shown.
- Source evidence:
  - `src/cobol/operations.cob` L24 — `ADD AMOUNT TO FINAL-BALANCE` without `ON SIZE ERROR`; target `PIC 9(6)V99`
  - Runtime: `999000` → `000000.00`; `999999` → `000999.00`; `99999.99` → `100999.99` (no overflow)
- Examples:
  - Given balance 1000.00, When crediting `999000`, Then `Amount credited. New balance: 000000.00`.
  - Given balance 1000.00, When crediting `999999`, Then new balance 999.00.
- Confidence: high
- Requirement candidate: yes (D4 preserve)

### RULE-011 — Debit eligibility: balance ≥ amount

- Type: eligibility
- Evidence state: observed
- Plain language: A debit is allowed only when the current balance is greater than or equal to the amount; equality is allowed.
- Source evidence:
  - `src/cobol/operations.cob` L32 — `IF FINAL-BALANCE >= AMOUNT`
  - Runtime: debit `1000` on 1000.00 → `000000.00`; debit `2000` → insufficient
- Examples:
  - Given balance 1000.00, When debiting `1000.00`, Then the debit succeeds and balance is 0.00.
- Confidence: high
- Requirement candidate: yes

### RULE-012 — Successful debit subtracts the amount

- Type: calculation
- Evidence state: observed
- Plain language: When eligible (RULE-011), the amount is subtracted, stored, and `Amount debited. New balance: <amount>` is printed.
- Source evidence:
  - `src/cobol/operations.cob` L33–35 — `SUBTRACT`, `CALL 'DataProgram' USING 'WRITE'`, `DISPLAY "Amount debited. New balance: "`
- Examples:
  - Given balance 1100.00, When debiting `50`, Then `Amount debited. New balance: 001050.00`.
  - Given balance 1000.00, When debiting `0`, Then balance stays 1000.00 and the debited message is shown.
- Confidence: high
- Requirement candidate: yes

### RULE-013 — Insufficient funds rejects the debit

- Type: validation / error handling
- Evidence state: observed
- Plain language: When balance < amount, nothing is stored and `Insufficient funds for this debit.` is printed; the menu continues.
- Source evidence:
  - `src/cobol/operations.cob` L36–37 — `ELSE DISPLAY "Insufficient funds for this debit."` (no WRITE)
- Examples:
  - Given balance 1000.00, When debiting `2000`, Then `Insufficient funds for this debit.` and a following `1` shows 1000.00.
- Confidence: high
- Requirement candidate: yes

### RULE-014 — Amount input parsing (GnuCOBOL ACCEPT into `PIC 9(6)V99`)

- Type: validation
- Evidence state: observed (runtime) — source only shows `ACCEPT AMOUNT` into unsigned `PIC 9(6)V99`
- Plain language: The amount line is interpreted as follows (amended 2026-10-20 after differential fuzzing in `modernize-transform`):
  1. Only the **first 8 characters** are considered (field length of `9(6)V99`); the rest is ignored.
  2. Special case: if those 8 characters are any character other than `.` followed by **7 digits**, the first character is ignored and the 7 digits are the integer part (e.g. `a1234567` → 234567.00).
  3. Otherwise: leading spaces are skipped; then one optional `+`/`-` is accepted and discarded (value is always positive). A sign anywhere else (including after a comma) makes the amount 0.
  4. Spaces and `,` are ignored at any position after that (`1 2` → 12, `1,5` → 15).
  5. `.` is the decimal point; once 2 fractional digits are read, all remaining characters are ignored, even invalid ones (`.3148a5.` → 0.31). Fewer than 2 fractional digits are zero-filled.
  6. Integer digits beyond 6 keep the low-order 6.
  7. Before the 2nd fractional digit, any other character (letter, `e`, misplaced sign, second `.`) makes the whole amount **0**; an input with no digits is 0.
- Source evidence:
  - `src/cobol/operations.cob` L7 — `AMOUNT PIC 9(6)V99`; L22, L30 — `ACCEPT AMOUNT`
  - Runtime (credit on 1000.00; amount = new balance − 1000 unless overflow):

    | Input | Amount used | Explains |
    | --- | --- | --- |
    | `500` | 500.00 | normal |
    | `1.5` / `.5` | 1.50 / 0.50 | decimal point |
    | `12.345` | 12.34 | step 4 |
    | `99999.999` | 99999.99 | step 1+4 |
    | `999999.99` | 999999.90 | step 1: first 8 chars `999999.9` |
    | `123456.78` | 123456.70 | step 1 |
    | `000000.01` | 0.00 | step 1: `000000.0` |
    | `1234567.89` | 234567.00 | step 1 (`1234567.`) + step 5 |
    | `12345678` | 345678.00 | step 5 |
    | `-50` / `+5` | 50.00 / 5.00 | step 2 |
    | ` 5` / `5 ` | 5.00 | step 2 |
    | `1,5` | 15.00 | step 3 |
    | `abc`, `12a`, `a12`, `1e3`, `5-`, empty | 0.00 | step 6 |
    | debit `-50` | 50.00 | step 2 (balance 950.00) |
    | debit `1000.001` | 1000.00 | step 4 |

- Examples:
  - Given balance 1000.00, When crediting `999999.99`, Then new balance is 999.90 (999999.90 + 1000.00 overflow per RULE-010).
  - Given balance 1000.00, When debiting `-50`, Then `Amount debited. New balance: 000950.00`.
  - Given balance 1000.00, When crediting `abc`, Then balance stays 1000.00 and the credited message is shown.
- Confidence: high (amended rule matches the legacy binary on 12,000 random inputs over `0-9+-., a*`, length 0–12, seeds 7/11/23/99 — 0 mismatches; pinned in `modernized/tests/test_numeric*.py`)
- Requirement candidate: yes (D3 preserve)

### RULE-015 — Amount is always requested, even before the balance check

- Type: other (sequencing)
- Evidence state: observed
- Plain language: For credit and debit, the amount prompt and input happen before the balance is read; a debit is never refused before the amount is entered.
- Source evidence:
  - `src/cobol/operations.cob` L21–23, L29–31 — `DISPLAY`/`ACCEPT` precede `CALL 'DataProgram' USING 'READ'`
- Examples:
  - Given balance 0.00, When selecting `3`, Then `Enter debit amount: ` is still printed.
- Confidence: high
- Requirement candidate: yes

### RULE-016 — Balance persists across operations within one run only

- Type: state-transition
- Evidence state: observed
- Plain language: Updates are kept in memory for later operations in the same run and are lost when the program ends.
- Source evidence:
  - `src/cobol/data.cob` L6 — `STORAGE-BALANCE` in WORKING-STORAGE (retained across `CALL`s), no file/DB I/O in any program
  - Runtime: `2`/`100`, `3`/`50`, `1` → `001100.00`, `001050.00`, `Current balance: 001050.00`
- Examples:
  - Given a fresh run, When crediting 100 then debiting 50 then viewing, Then the balance shown is 1050.00.
  - Given a previous run ended with 1050.00, When a new run starts, Then the balance is 1000.00 (RULE-001).
- Confidence: high
- Requirement candidate: yes (D5)

### RULE-017 — Amount display format

- Type: other (output contract)
- Evidence state: observed; **intentional change approved (D2)**
- Plain language: Legacy prints amounts as `PIC 9(6)V99` display: 6 zero-padded integer digits, `.`, 2 decimals (e.g. `001000.00`, `000000.00`). The target prints the same value without leading zeros, always with 2 decimals (`1000.00`, `0.00`).
- Source evidence:
  - `src/cobol/operations.cob` L18, L26, L35 — `DISPLAY ... FINAL-BALANCE`
  - Runtime: `Current balance: 001000.00`; `New balance: 000000.00`
  - `analysis/account-system/BRIEF.md` — Decision D2
- Examples:
  - Given balance 1000.00, When viewing, Then legacy prints `001000.00` and target prints `1000.00`.
  - Given balance 0.00, When viewing, Then target prints `0.00`.
- Confidence: high
- Requirement candidate: yes (changed)

### RULE-018 — End of input causes an endless invalid-choice loop

- Type: error handling
- Evidence state: observed (runtime)
- Plain language: If stdin ends before option 4, every further `ACCEPT` yields an invalid choice; the menu and `Invalid choice, please select 1-4.` repeat forever.
- Source evidence:
  - `src/cobol/main.cob` L11, L20, L31–32 — loop exits only via `CONTINUE-FLAG = 'NO'`; no EOF handling
  - Runtime: `printf '1\n' | timeout 3` → 6,588,721 lines, rc 124; menu probe `3a` → 849,936 invalid messages
- Examples:
  - Given input `1` then EOF, When the program runs, Then it never terminates on its own.
- Confidence: medium (output repetition observed; whether ACCEPT returns space or keeps the old value at EOF is not visible — outcome is the same)
- Requirement candidate: yes (changed) — intentional change D8 / DESIGN C2: target prints the goodbye line and exits 0 on EOF at the menu

## Cross-Rule Notes

- RULE-014 feeds RULE-009/010/011/012: parse first, then apply arithmetic; overflow (RULE-010) applies only to credit — debit cannot go below 0 because of RULE-011.
- Messages are the observable contract; credit/debit print success messages even for amount 0 (RULE-009, RULE-012).
- Literal mismatch `'READ'`/`'WRITE'` vs `PIC X(6)` (`operations.cob` L17, L23, L25, L31, L34; `data.cob` L10) has no observable effect; excluded as a rule (implementation detail).
- No authorization, audit, temporal, or multi-account rules exist in the source.
- Differential tests must normalize amount formatting (RULE-017) and stop the legacy binary before EOF (always end scripts with `4`) because of RULE-018.

## Low-Confidence Questions

| Rule | Question | Why it matters | Owner |
| --- | --- | --- | --- |
| RULE-014 | Add a combinatorial golden-master corpus for untested input shapes? | Parser rules are inferred from 20 samples | Developer |
| RULE-005 | Pin GnuCOBOL 3.1.2 as the oracle version? | ACCEPT semantics may differ across versions/dialects | Developer |

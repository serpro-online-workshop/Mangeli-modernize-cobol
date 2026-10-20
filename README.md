# Modernize your legacy code with GitHub Copilot

<img src="https://octodex.github.com/images/Professortocat_v2.png" align="right" height="200px" />

Hey EduardoMangeli!

Mona here. I'm done preparing your exercise. Hope you enjoy! 💚

Remember, it's self-paced so feel free to take a break! ☕️

[![](https://img.shields.io/badge/Go%20to%20Exercise-%E2%86%92-1f883d?style=for-the-badge&logo=github&labelColor=197935)](https://github.com/serpro-online-workshop/Mangeli-modernize-cobol/issues/1)

## Python version of the account system

The COBOL program in `src/cobol/` has been rewritten in Python 3.10 (standard library only) in `modernized/account_system.py`. Analysis, rules, and approved behavior changes are in `analysis/account-system/`.

Run:

```bash
python3.10 modernized/account_system.py
```

Test (from the repository root):

```bash
python3.10 -m venv .venv
.venv/bin/pip install -r modernized/requirements-dev.txt
cd modernized
../.venv/bin/ruff check .
../.venv/bin/pytest -q --cov=account_system --cov-branch
```

The differential tests compile `src/cobol/` with GnuCOBOL (`cobc`) and compare full sessions with the Python program. They are skipped when `cobc` is not installed; run only the other tests with `pytest -m "not differential"`.

Approved differences from the COBOL program: amounts are shown as `1000.00` instead of `001000.00`, and the program says goodbye and exits with code 0 when input ends at the menu (the COBOL program loops forever).

Rollback: the COBOL program is unchanged and still builds with `cobc -x src/cobol/main.cob src/cobol/operations.cob src/cobol/data.cob -o accountsystem`.

---

&copy; 2025 GitHub &bull; [Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md) &bull; [MIT License](https://gh.io/mit)


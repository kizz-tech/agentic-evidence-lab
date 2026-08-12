## Intent

What decision, defect, or research question does this change address?

## Evidence and claim scope

- What changed?
- What was held fixed?
- What do the checks prove, and what do they not prove?

## Validation

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run python -m unittest discover -s tests -v`
- [ ] `uv run ael validate examples`
- [ ] `uv run ael study audit --freeze <freeze.json> --result <result-dir>` for changed frozen results
- [ ] `python tools/release_check.py`
- [ ] User-visible changes are in `CHANGELOG.md`
- [ ] No secrets, private captures, hidden holdouts, or personal paths are included

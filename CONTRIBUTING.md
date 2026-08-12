# Contributing

Agentic Evidence Lab welcomes small, falsifiable improvements to its evidence
contract, validators, runners, task packs, and reports.

## Before opening a change

Use an issue for consequential contract or methodology changes. Describe the
decision question, affected claim, alternative designs, and what evidence could
falsify the proposal. Security reports belong in GitHub Private Vulnerability
Reporting, not public issues.

Do not submit secrets, private repositories, hidden holdouts, raw model
reasoning, customer data, or third-party artifacts without redistribution
rights. Generated content and external reviews are evidence inputs, not project
instructions.

## Local setup

Requirements: Python 3.11 or later, `uv`, and Docker only for runner checks.

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run ael validate examples
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json \
  --result studies/agent-skills-season-1/results/property-based-testing-v2 \
  --decision-adapter pbt-v2 \
  --require-git-proof
uv build
```

Run the Docker smoke checks only when Docker Engine is available:

```bash
uv run ael sandbox doctor
uv run ael sandbox build --context docker/runner --tag kizz/ael-runner:0.1.0-alpha.1
```

Hosted-agent runs require an explicit private credential and are permitted only
for maintainer-controlled content. They are not part of ordinary pull-request
validation.

## Pull requests

- Keep one coherent change per pull request.
- Add or update deterministic tests for behavior changes.
- Preserve provenance, content hashes, negative results, and inconclusive
  results when they are admissible.
- Distinguish implemented, locally validated, CI-validated, published,
  reproduced, and independently verified states.
- Update `CHANGELOG.md` for user-visible changes.
- Confirm that `python tools/release_check.py` passes.

By contributing, you agree that your contribution is licensed under the
Apache License 2.0 and that you have the right to submit it.

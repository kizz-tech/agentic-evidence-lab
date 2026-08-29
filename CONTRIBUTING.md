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
uv run ael study preflight \
  studies/quality-preflight/examples/pass/quality-profile.json \
  --json-output studies/quality-preflight/examples/pass/preflight.json \
  --markdown-output studies/quality-preflight/examples/pass/preflight.md \
  --check
uv run ael results check studies/public-results.json --require-git-proof
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

### AEL-CEP changes

AEL-CEP is a family-local sidecar, not a sixth Contract v0 document. For
changes to its protocol, bundle adapter, simulator, schemas, or fixtures, run
the dedicated protocol/bundle validation and deterministic Stage 0 simulator
gate described in [Reproducibility](docs/reproducibility.md). The exact CLI
entry points and input ceilings are maintained in that reproducibility
document; generic `ael validate examples` does not validate AEL-CEP sidecar
artifacts.

## Pull requests

- Keep one coherent change per pull request.
- Add or update deterministic tests for behavior changes.
- Preserve provenance, content hashes, negative results, and inconclusive
  results when they are admissible.
- Distinguish implemented, locally validated, CI-validated, published,
  reproduced, and independently verified states.
- Update `CHANGELOG.md` for user-visible changes.
- For AEL-CEP changes, include the exact local protocol, deterministic-simulator,
  and no-effect validation evidence in the pull request; do not describe Stage
  0 output as empirical superiority, real custody, or production safety. State
  that sufficient-stat arithmetic/hash closure covers materialized rows and
  dependencies only; it does not prove unmaterialized external events.
- For bridge or promotion changes, retain the complete weighted panel,
  candidate-keyed transition/effect containment evidence, and the
  dependency-bound, recomputed `contrast_summary` seal and its exact
  trajectory-row dependencies; it is not an authority-bearing promotion
  decision and a scalar
  bridge or arbitrary report metric is not an acceptable substitute. The core
  derives operating metrics, primary endpoints, and contrast diagnostics from
  that seal only. Document `false_promotion_share` as invalid promotions over
  all candidate promotions and `invalid_candidate_promotion_rate` as invalid promotions
  over invalid candidate opportunities; candidate opportunities are distinct
  from task-level disposition. Primary endpoints use exact
  `sum_ppm`/`observed_count`; optional stopping or actual-cost mismatch is
  diagnostic-only, and any missing compared arm/scenario endpoint is not
  estimable. Derive global
  shift, interaction, evaluator decision, and anchor decision gates per stratum
  so weighted aggregation cannot cancel a failing stratum; bind each B0/B1
  anchor to its exact subject-evidence ref/hash. Preserve the independent named
  anchor-truth stream and two-phase evidence/anchor-before-score ordering,
  positive promotion to bridge B1, and role-level custody semantics (same-role
  generation reuse is allowed).
- Treat `synthetic_pass`/`synthetic_fail` construct and reliability statuses as
  local fixtures, never empirical calibration or validity evidence. If the
  dependency-bound `contrast_summary` is revoked, tainted, or unscorable, all
  derived metrics/endpoints/diagnostics are unavailable; do not substitute
  stale, scoped, or nested summaries. Generic `ael validate` does not accept a
  CEP directory; use `ael coevolution check`.
- Treat the CLI and versioned CEP file/schema formats as the alpha.12 public
  contract. Direct imports from `ael.coevolution*` are repository-internal and
  may change without compatibility shims; propose a Python facade only with a
  concrete separately owned consumer and use case.
- Keep `confirmation_eligible` pre-confirmation: it must not consume or anchor.
  A passing candidate gets exactly one candidate-bound pack, irreversibly
  reserved/marked used before the final decision set (`promote`, `narrow`,
  `abstain`, `reject`). A recorded exposure blocks a positive `promote` only
  when its target resolves to the sealed confirmation task root before that
  decision; screening and bridge exposures remain allowed under their own
  budgets and lifecycle. A failed bridge starts `new_measurement_epoch`, and
  an early eligible-state revoke requires an authority-bound
  `deletion_tombstone`.
- Confirm that `python tools/release_check.py` passes.

By contributing, you agree that your contribution is licensed under the
Apache License 2.0 and that you have the right to submit it.

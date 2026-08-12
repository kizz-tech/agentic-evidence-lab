# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Reorganized the public documentation around decision-ready results, direct
  usage guidance, layered evidence access, and goal-based navigation.

## [0.1.0-alpha.1] - 2026-08-12

### Added

- Contract v0 JSON Schemas and cross-document validation for concepts, studies,
  runs, measurements, and evidence receipts.
- Deterministic receipt rendering and simulation-based study calibration.
- Sanitized Council Generation 1 mapping and a six-cell Codex skill calibration.
- Docker offline runner, controlled-egress Codex adapter, task-pack checks, and
  explicit trusted-input acknowledgement for hosted runs.
- Validated staging export that rejects symlinks, special entries, and reserved
  host metadata paths before copying container output.
- Strict JSON parsing, validation-root confinement, and local-reference symlink
  rejection for public evidence documents.
- A public Results Index and contract for task-specific, evidence-backed
  leaderboards.
- Public methodology, reproducibility, security, governance, and contribution
  documentation.

### Known limitations

- The first Codex calibration has a ceiling effect and does not demonstrate a
  treatment win.
- Hosted runs are restricted to maintainer-controlled content because the agent
  process can read the reusable credential.
- Contract v0 remains pre-stable and may change incompatibly before `1.0`.

[Unreleased]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.1...HEAD
[0.1.0-alpha.1]: https://github.com/kizz-tech/agentic-evidence-lab/releases/tag/v0.1.0-alpha.1

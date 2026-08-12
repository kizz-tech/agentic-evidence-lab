# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A generic, fail-closed study-freeze contract with exact schedule coverage,
  private-pack digests, code and prompt hashes, sequential stop rules, and
  hash-bound observation identity.
- A preregistered Property-based Testing v2 pathfinder with four private
  screening tasks, two inaccessible confirmation tasks, a matched baseline,
  and zero scored calls at freeze.
- Study-local PBT runner, deterministic decision code, evidence materializer,
  and CI checks that bind the public freeze to the current implementation.

### Research notes

- Truthful-completion sacrificial calibration stopped before freezing because
  the baseline produced no unsupported completion claims on either candidate
  prompt. This is a task-design ceiling finding, not a skill-effect result.

## [0.1.0-alpha.2] - 2026-08-12

### Added

- Agent Skills Season 1 with ten bounded study protocols, twelve exact upstream
  source registrations, ten Contract v0 draft manifests, and a public ten-task
  calibration pack.
- Twenty-two retained Season 1 Codex activation records, ten measurement sets,
  ten evidence receipts, and an activation matrix that keeps effectiveness and
  leaderboard claims explicitly unrun.
- Revisioned invalidation records for an underdetermined truthful-completion
  prompt and an external-resource evaluator false positive.
- `ael source-lock` validation and non-executing checkout verification for
  external skill provenance and execution eligibility.

### Changed

- Reorganized the public documentation around decision-ready results, direct
  usage guidance, layered evidence access, and goal-based navigation.
- Staged task-pack evaluators inside the validated private output root so the
  symlink fail-closed policy works with macOS system temporary paths.
- Versioned study resolution now uses the exact `(study_id, revision)` pair so
  immutable activation and later screening manifests can coexist.
- Private screening and confirmation packs are physically outside the Git
  worktree; the release scan rejects reserved private-evidence canaries.

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

[Unreleased]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.2...HEAD
[0.1.0-alpha.2]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/kizz-tech/agentic-evidence-lab/releases/tag/v0.1.0-alpha.1

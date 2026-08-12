# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha.5] - 2026-08-12

### Added

- An explicit public-results profile and deterministic `ael results` projection
  that generate the human Results Index, per-study cards, and a machine-readable
  index from hash-bound Contract v0 evidence.
- Per-study verification boundaries and unavailable-material disclosures that
  distinguish evidence-graph checks from model reruns and independent
  replication.
- Release gates for frozen historical result bytes and the contents, metadata,
  checksums, and provenance manifest of built wheel and source archives.

### Changed

- Current public navigation is now derived from three deliberately admitted
  result families instead of duplicate hand-maintained finding tables.
- Publication status, freshness, decision admission, actual action, and outcome
  follow-up are displayed as separate facets; unavailable historical facts stay
  explicitly undeclared instead of being inferred from old receipt prose.
- Season 1 navigation now distinguishes activation compatibility from
  effectiveness and records the completed bounded negative PBT v2 result.

### Research integrity

- Contract v0's five schemas, the receipt renderer, and the alpha.3/alpha.4
  frozen evidence remain unchanged. Result cards are disposable projections and
  cannot raise the evidence level or claim level recorded by a receipt.
- Git verification is described as repository artifact ordering, not as
  independent proof of when private model execution occurred.

## [0.1.0-alpha.4] - 2026-08-12

### Added

- `ael study audit`, a single fail-closed verifier for a frozen study and its
  terminal public result bundle, including exact schedule, reference, receipt,
  decision-alias, private-pack digest, and Git preregistration lineage checks.
- An explicit `pbt-v2` decision adapter that reconstructs counts and the
  terminal outcome from individual run records, evaluator-owned measurements,
  and the frozen rule instead of trusting aggregate fields alone.
- `ael study activation-check`, which treats only successful completed Codex
  commands with non-empty exact `SKILL.md` retrieval as activation evidence.

### Changed

- CI and clean-wheel validation now audit the published Property-based Testing
  v2 bundle with full Git history and require preregistration proof.
- Ruff's supported maintenance range now extends through `0.16.x`; the lockfile
  is updated with the release.

### Research integrity

- The alpha.3 freeze, result bytes, runner, decision code, and private raw packs
  remain unchanged. Alpha.4 adds verification around the historical negative
  result and does not reinterpret it as new experimental evidence.

## [0.1.0-alpha.3] - 2026-08-12

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
- The PBT pilot stopped after eight valid repeat-1 cells. All four matched pairs
  tied on hidden acceptance, while both conditions produced two incompatible
  added-test failures; the frozen rule therefore rejected the treatment and
  kept repeat 2 and confirmation locked.

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

[Unreleased]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.5...HEAD
[0.1.0-alpha.5]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.4...v0.1.0-alpha.5
[0.1.0-alpha.4]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.2...v0.1.0-alpha.3
[0.1.0-alpha.2]: https://github.com/kizz-tech/agentic-evidence-lab/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/kizz-tech/agentic-evidence-lab/releases/tag/v0.1.0-alpha.1

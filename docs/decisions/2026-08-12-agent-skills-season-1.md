# Agent Skills Season 1 architecture

Status: accepted and activation-calibrated; discriminating effectiveness
screening remains unrun.

## Decision

Implement Season 1 as ten independent, versioned study dossiers composed over
the existing AEL evidence kernel. Do not create a skill marketplace, package
manager, plugin SDK, workflow DSL, generic metric ontology, or global
leaderboard.

The stable shared surface is intentionally narrow:

```text
source lock → study manifest → runner artifact → study evaluator → receipt
```

- The source lock is a provenance and eligibility record, not an installer.
- Operators provide exact Git checkouts; AEL verifies commit, source-path tree
  hash, and observed license evidence without executing repository code.
- Each study owns its hypothesis, task strata, metrics, failure gates,
  statistical plan, compatibility adaptations, and interpretation.
- Public calibration tasks prove mechanics only. Hidden screening and
  confirmation packs remain outside public Git history and are represented by
  immutable opaque references in receipts.
- Conditions share a frozen base snapshot. Every changed prompt, skill,
  context, tool, runtime, permission, topology, or budget factor must be named.
  A placebo exists only for a prespecified confound.
- Results become contextual boards only inside one frozen comparison contract.

## Why

The ten studies cover coding behavior, debugging, testing, security reports,
multi-agent review, protocol construction, browser evidence, subjective design,
and recursive artifact improvement. Their common lifecycle is real; a common
definition of “quality” is not. Generalizing workflow topology, evaluator
semantics, or scores before two concrete studies need the same invariant would
manufacture comparability and transfer capability ownership into AEL.

The first Focused Change Verification calibration also demonstrated that
pipeline success is not experimental success: public prompts prescribed much
of the target behavior, baseline hit a ceiling, and the correct result was to
reject the pack as an effect test. Season 1 therefore makes mechanics,
screening, and confirmation distinct stages.

## Security state machine

Third-party sources move through explicit states:

```text
metadata_registered → quarantined → verified_snapshot → execution_eligible
```

Registration never implies execution eligibility. Acquisition must not run
hooks, build scripts, package scripts, or submodules. Source and task inputs are
read-only; workspace and output are bounded and disposable; network defaults to
none; host home, Codex home, Docker socket, broad environment, and reusable
secrets are forbidden.

The existing hosted Codex path is limited to exact source-locked snapshots that
the maintainer reviewed and explicitly accepted for maintainer-controlled
execution. Its agent process can read a reusable credential; exact-host egress
allowlisting and persisted-output secret scans do not prevent encrypted
exfiltration to an allowed host. Arbitrary submissions therefore remain
blocked, while the accepted pinned Season 1 snapshots may run under this
disclosed boundary.

## Implemented now

- one exact source lock for twelve skill trees from four upstream repositories;
- non-executing checkout verification in the CLI;
- ten protocol dossiers and ten Contract v0 draft manifests;
- one public ten-task calibration pack with separate evaluators;
- reproducible manifest materialization and CI checks;
- a macOS-safe evaluator staging fix that preserves symlink fail-closed rules.
- 22 valid activation-calibration records and ten evidence receipts;
- two retained invalidated revisions that exposed task/evaluator defects;
- observed explicit skill reads for ten of twelve treatment snapshots.

## Deferred until demonstrated need

- automatic source fetching, mirroring, caching, or package installation;
- a universal study runner or evaluator plugin API;
- multi-agent topology and recursive-improvement DSLs;
- browser or MCP services beyond study-owned runner images;
- a database, scheduler, hosted control plane, dashboard, or universal score.

Extract a shared abstraction only after two completed studies exhibit the same
semantic invariant and change pressure. If a shared field acquires
study-specific modes, move it back into the study dossier.

## Reversal and publication hazards

Directory layout, TOML shape, CLI spelling, and study-local scripts are
reversible. The following are costly or impossible to reverse after release:
leaked hidden tasks, leaked credentials, incorrect license or safety claims,
silently changed treatment identity, and a public score implying unsupported
cross-study comparability. These remain fail-closed publication gates.

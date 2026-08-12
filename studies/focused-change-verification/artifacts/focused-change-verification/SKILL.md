---
name: focused-change-verification
description: Verify a completed or proposed repository change at the narrowest sufficient owner layer, then report exact validation state. Use for code changes, bug fixes, refactors, contracts, schemas, migrations, configuration, and release preparation when Codex must select relevant checks without claiming more than the evidence proves.
---

# Focused Change Verification

Verify the effect owned by the changed component, its direct contracts, and the
consumers that can materially break. Keep local proof, release state, runtime
state, and user outcome separate.

## Workflow

1. Read the request, repository instructions, current diff, and relevant owner
   files. Do not infer the change only from filenames.
2. Identify the owning layer and the changed contract: behavior, public API,
   schema, migration, configuration, generated artifact, or infrastructure.
3. Trace only material propagation: direct callers, consumers, persistence,
   serialization, generated code, deployment wiring, and rollback path.
4. Choose the smallest check set that can falsify the intended effect and the
   most expensive plausible regression.
5. Run cheap owner-local checks first. Broaden when the changed boundary,
   failure evidence, or repository policy requires it.
6. Preserve failures and distinguish product defects from environment,
   dependency, fixture, or operational invalidity. Do not rerun a poor result
   merely to obtain a pass.
7. Report exactly what was inspected, executed, passed, failed, and not proven.

## Minimum routing

- Local implementation change: targeted unit tests plus the owning package's
  lint or type check when applicable.
- Shared API or type contract: provider checks and at least one direct consumer
  compile, type, contract, or integration check.
- Persistence or migration: migration syntax/order, forward application in a
  disposable database, compatibility with the application revision, and a
  declared rollback or forward-repair path.
- Configuration or dependency change: parser/lock validation and the narrowest
  startup or build path that consumes it.
- Cross-cutting refactor: targeted tests for each changed boundary, then the
  repository's shared build/test gate if the dependency surface warrants it.
- Security, money, destructive effects, concurrency, or production behavior:
  stop treating the task as routine and require the owning high-risk checks.

Repository-specific instructions override this routing when they are more
protective. A passing narrow check does not prove untouched layers.

## Scope and safety

- Do not deploy, push, publish, migrate production data, rotate credentials, or
  perform another external mutation unless the user separately authorizes it.
- Do not expose secrets in commands, logs, reports, or committed artifacts.
- Do not modify unrelated user work to make validation pass.
- Use disposable environments for migrations, untrusted tools, and destructive
  fixtures.
- If a required check cannot run, state the blocker and the unproven claim; do
  not substitute a weaker check silently.

## Result contract

Return:

1. intended effect and owning layer;
2. checks run with exact scope and result;
3. failures or integrity limitations;
4. state: prepared, implemented, locally validated, committed, pushed,
   deployed, runtime-observed, or outcome-proven;
5. residual risks and the smallest next check, if any.

Never collapse those states into “done.”

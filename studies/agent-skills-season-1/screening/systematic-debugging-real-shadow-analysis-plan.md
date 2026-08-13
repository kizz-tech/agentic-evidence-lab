# Systematic-debugging real-shadow v1 analysis plan

Status: prospective pilot; no scored calls had been executed when this plan, its manifest, admission, and freeze were created.

## Decision and boundary

The pilot asks whether adding the exact source-locked Superpowers `systematic-debugging` tree to an otherwise identical Codex stack changes deterministic root-cause-correct repair on four sanitized incidents enough to justify one reversible Kizz owner action.

This is a decision pilot, not a population estimate, benchmark, leaderboard, or claim about debugging skills in general. `install_globally` is ineligible regardless of outcome. The strongest permitted action is selective routing of the exact snapshot for the exact admitted stratum.

## Factor and execution

- `B0`: Codex CLI `0.146.0`, `gpt-5.6-sol`, `xhigh`, no injected study skill.
- `S1`: the same stack plus only the exact source-locked `systematic-debugging` tree.
- Four private sanitized tasks: two `cross-boundary-contract`, two `state-order-lifecycle`.
- One repeat per condition and task: eight scored calls in a deterministic hash-keyed order.
- Same prompt, task bytes, tools, Docker images, network policy, timeout, and generated-token cap in both conditions.
- Agent execution receives no evaluator bytes. Deterministic evaluation occurs later in an offline Docker container without credentials or network.

Existing public activation calibration is the mechanics and token/latency calibration for this skill. It is excluded from all effect counts.

## Endpoint and gates

The primary endpoint is binary deterministic acceptance: visible checks pass, the hidden causal invariant passes, preserved tests remain compatible with the reference root-cause repair, and the change stays within the task's safe file scope.

For each matched task:

- favorable: `B0` is not accepted and `S1` is accepted;
- unfavorable: `B0` is accepted and `S1` is not accepted;
- tie: both are accepted or both are not accepted.

Critical treatment gates are failed reference compatibility, unsafe/destructive file scope, credential persistence, fixture mutation, absent treatment activation, or any invalid cell.

## Frozen effect rule

- `bounded_favorable_signal`: both tasks in at least one stratum are favorable, every cell is valid, every treatment activates, there are zero unfavorable pairs, and there are zero treatment critical failures.
- `treatment_harm_signal`: at least two pairs are unfavorable.
- `treatment_critical_failure`: any treatment critical gate fires.
- `treatment_activation_failure`: any valid treatment cell lacks observed skill activation.
- `mixed_or_no_headroom`: every other valid result.
- `invalid_manual_review`: any cell is operationally invalid.

The preregistered owner policy maps these effect outcomes to a separate adoption decision. A bounded favorable signal can only produce `route_selectively` for the qualifying strata. Harm, critical, or activation failure produces `reject_exact_version`. Mixed/no-headroom produces `keep_optional`. Invalid evidence stops automatic action.

## Retry, stop, and chronology

No model outcome is retried. The runner rejects non-empty cell and run-set paths rather than silently resuming or replacing evidence. It stops the schedule after an invalid cell. A future byte-equivalent rerun would require explicit reconciliation and a new recorded run-set; it is not part of this freeze.

The Git preregistration commit proves repository artifact ordering: exact admission, manifest, freeze, code, and plan bytes precede committed result artifacts. Per-cell UTC timestamps are operator-recorded metadata. Neither mechanism independently proves the absolute time of all private model calls.

## Independence, privacy, and follow-up

Kizz authors the sanitized task pack and evaluator, operates the runner, and owns the decision and action. The result is maintainer-evaluated and not independent replication. Private tasks, dossiers, raw events, candidates, scores, and authentication remain outside public Git and are projected only as opaque hashes.

The owner explicitly accepts use of reusable local Codex authentication for this exact reviewed MIT snapshot, four sanitized maintainer-controlled fixtures, and at most eight scored calls through the host allowlist proxy. This admission does not authorize arbitrary third-party submissions.

Any selective route remains opt-in, preserves a baseline fallback, and is followed for the next ten eligible natural cases or through 2026-09-12, whichever comes first. Repair acceptance, rework/regression, time cost, and critical failures are observed separately. This follow-up does not retroactively upgrade the study evidence.

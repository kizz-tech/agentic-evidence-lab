# Council Generation 1

- Card ID: `council-generation-1`
- Current publication: **published**
- Receipt: [machine-readable evidence](../../examples/council-generation-1/evidence-receipt.json)
- Receipt SHA-256: `8cb13547dda6dc8a8805fe65587c6f3c8712ca81a32cff45a57874c76a59a757`
- Report: [narrative result](../../reports/2026-08-12-council-generation-1.md)
- Evidence level: `controlled_effect_observed`
- Reproducibility: `rerunnable`
- Independence: `maintainer_evaluated`

## Decision

**adopt** — Adopt the frozen adaptive routing and integration semantics for the local Engineering Council because the candidate preserved measured held-out quality, repaired an observed profile-execution defect, routed the routine case directly, and cleared the predeclared generated-work gate on the two consequential cases.

Scope:
- the exact Council Generation 1 candidate artifact
- the measured Codex CLI and gpt-5.6-sol configuration
- three synthetic held-out engineering cases
- local replacement of the historical engineering-council skill

Reversal trigger: Reopen the decision if the artifact, model/runtime surface, task pack, or execution contract changes, or if repeated real-shadow evidence exposes a quality, conformance, or downstream-rework regression.

## What was tested

Should the historical Engineering Council workflow be replaced by the frozen adaptive candidate, retained unchanged, or replaced by a fixed sequential workflow on the measured local Codex surface?

Comparison mode: `controlled_factor`. Study state: `completed`.

Primary estimand: **heldout decision quality and process acceptability** — Compare the frozen candidate with direct, sequential, and historical-skill conditions on held-out engineering cases while preserving critical-anchor, routing, and generated-work constraints.

Conditions:
- `C0` — Direct single pass (`baseline`)
- `C1` — Fixed sequential revision (`control`)
- `C2` — Historical skill-routed workflow (`control`)
- `C3` — Frozen adaptive council candidate (`treatment`)

Task strata:
- `engineering-council-generation-1-heldout` (`holdout`): routine-local, consequential-domain-policy, consequential-performance

Decision owner(s): `kizz-council-maintainer`

## Runs and measurements

Runs: `12`; by status: `valid=12`.

Measurements: `46`; by kind: `aggregate=7`, `cost=12`, `process=3`, `subjective=24`.

Selected descriptive totals (not stable effects):

- `consequential_generated_work_tokens` / `C2`: total `12560 tokens` (`cost_or_latency`)
- `consequential_generated_work_tokens` / `C3`: total `9598 tokens` (`cost_or_latency`)
- `critical_anchor_misses` / `C0`: total `0 count` (`critical_failure`)
- `critical_anchor_misses` / `C1`: total `0 count` (`critical_failure`)
- `critical_anchor_misses` / `C2`: total `0 count` (`critical_failure`)
- `critical_anchor_misses` / `C3`: total `0 count` (`critical_failure`)
- `generated_work_tokens` / `C0`: total `3637 tokens` (`cost_or_latency`)
- `generated_work_tokens` / `C1`: total `17219 tokens` (`cost_or_latency`)
- `generated_work_tokens` / `C2`: total `13187 tokens` (`cost_or_latency`)
- `generated_work_tokens` / `C3`: total `10257 tokens` (`cost_or_latency`)

## Claims

### AEL-CG1-01 — supported

The frozen candidate repaired the observed full-history named-profile execution and consultation-provenance defect on the measured local runtime surface.

Claim level: `workflow`

Falsifier: A hash-equivalent rerun reproduces the same full-history fork failure in the candidate or cannot authenticate any claimed consultation.

### AEL-CG1-02 — bounded

The candidate preserved measured held-out decision quality relative to the historical skill and fixed sequential revision under the frozen tie rule.

Claim level: `workflow`

Falsifier: Repeated held-out or real-shadow runs show a material quality or critical-failure regression against either strong control.

### AEL-CG1-05 — supported

Consultation identity and trace attribution remained incomplete even though the candidate improved process accountability.

Claim level: `artifact`

Falsifier: A future runtime and candidate revision provide authenticated receiver IDs and complete profile-scoped finding IDs on every applicable run.

## Verification boundary

Kind: `evidence_graph`

Validates the published Contract v0 graph and exact local reference hashes. It does not rerun the Council workflows, recover private held-out material, or independently reproduce the decision.

Command (presentation only; not executed by this generator):

```sh
uv run ael validate examples/council-generation-1
```

## Independence

The receipt is a content-addressed maintainer evaluation, not independent certification.

## Historical status

- admission: `not_declared_historical`
- action: `not_declared_historical`
- outcome_follow_up: `not_declared_historical`
- freshness: `unassessed`

## Materials

- **Synthetic held-out briefs and evaluator anchors** — `withheld`
  - Reason: The retained evaluation package is private and only its provenance hashes are public.
  - Reproduction impact: A public checkout can inspect normalized runs and measurements but cannot rerun the exact held-out cases.
- **Authenticated subagent receiver identities** — `not_collected`
  - Reason: The measured runtime event surface did not expose authenticated receiver identities.
  - Reproduction impact: Consultation identity and complete trace attribution cannot be independently reconstructed.

## Unsupported inferences

- Universal multi-agent or debate superiority
- Advisor-roster or prompt optimality
- Small-model councils replacing one capable model
- Research, product, design, or personal-domain transfer
- Universal compute or monetary cost reduction
- Production or downstream implementation outcome improvement
- Public reproducibility or independent verification

## Limitations

- One stochastic sample was collected per case and condition.
- The study used synthetic briefs rather than observed production decisions.
- Contestants and judge were correlated variants of the same model family.
- Total input compute was not equalized across conditions.
- No downstream implementation, rework, regression, or user outcome was measured.
- The retained event stream did not expose authenticated subagent receiver IDs.
- The candidate omitted exact profile identities and finding IDs in one held-out final.

## Invalidation triggers

- Any change to the candidate skill hash or roster/configuration hash
- A model, Codex CLI, tool-policy, or sandbox revision that changes observable behavior
- A task-pack, rubric, tie rule, or judge revision
- New repeated or real-shadow evidence showing a quality, safety, conformance, or rework regression
- A change in evaluator or maintainer role overlap that alters the evidence-strength claim

## Source hashes

- `examples/council-generation-1/concept.json` — `e9ea287b7c92822c0ca9f10edf93ac0882aa225e1006bf7ff05cf5e90f15db5e`
- `examples/council-generation-1/evidence-receipt.json` — `8cb13547dda6dc8a8805fe65587c6f3c8712ca81a32cff45a57874c76a59a757`
- `examples/council-generation-1/measurement-set.json` — `6f2f0a1b9af8605cabd2894bc587d14d38fb5c3b6024f6e1dcbc5cd4761cb5b0`
- `examples/council-generation-1/runs/E1-C0.json` — `eaef94912e9091823c5fbd27908f93b64e4274804466566aae5fa95fbdcbcc82`
- `examples/council-generation-1/runs/E1-C1.json` — `58aef5720b516e097b9b300ca2f06058f56d85359723defd4f9d50754bc22cc4`
- `examples/council-generation-1/runs/E1-C2.json` — `4d4c05cf3830c0949b4b503120b3fed7f0632bac75dad092142506056e2d274e`
- `examples/council-generation-1/runs/E1-C3.json` — `e14a5b5d01e3c612cfdb3c2164a82a15a07d5b40c28c9967f2e02edd786bce5b`
- `examples/council-generation-1/runs/E4-C0.json` — `0dc3e03de0059cbe72363a1ba5eaa7ebc6ba29e03c964efafb8cd9b925dc9183`
- `examples/council-generation-1/runs/E4-C1.json` — `2d2d00c657cdea42b0b43b65e851438b5ef5f17804f5beb7b72ff617ccb6b4d2`
- `examples/council-generation-1/runs/E4-C2.json` — `7100e198b510544f25af46882f336ed4b6f3ef542aeb8d2f6cfe6f837849dd0f`
- `examples/council-generation-1/runs/E4-C3.json` — `aa0917d3a74fa4772857ec0cfa2e4a4c4ba0a83e38f53dd995f8af69df2f5fa3`
- `examples/council-generation-1/runs/E7-C0.json` — `a85ece89eecc2b264f9e149483f5a439dee4b555645bb0eafe5e00d16c4fcca1`
- `examples/council-generation-1/runs/E7-C1.json` — `e2206759b9e59f7e1cd6e4993c933c5ee7f8dfec2e20c947e09c42c8d6db86e4`
- `examples/council-generation-1/runs/E7-C2.json` — `39a50aa93d760066b9b031d828f9aff443f64b51329cf92bc99365aaff62cd0e`
- `examples/council-generation-1/runs/E7-C3.json` — `fbc585cadc103cdd9726c9d8584cf06ba1727170f4b98d5202db146c726cd141`
- `examples/council-generation-1/study-manifest.json` — `aad0f01c68fc7346f0a834e7039f0650af31a04f65ceee927312468b335e9206`
- `reports/2026-08-12-council-generation-1.md` — `9e9114b8c42cc135890fba800257ea405df8ef7b68928bd6e405b4ff3844313a`
- `studies/public-results.json` — `6ce9dd76a68d966b916637ea93c102f9796865f9c4707aaa5f1ddd59f5eb8d76`

Generated by `agentic-evidence-lab` `0.1.0a5` under `ael.publication-projection/0.1`.

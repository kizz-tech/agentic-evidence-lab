# Completion Integrity prompt policy v1

- Card ID: `completion-integrity-prompt-policy-v1`
- Catalog state: **listed**
- Narrative report: [open](../../reports/2026-08-15-completion-integrity-prompt-policy-v1.md)

## Decision

**reject** — The exact policy failed the frozen effect or anti-abstention rule and is rejected.

Scope:
- the exact eight-task Completion Integrity v1 private pack
- the exact completion-policy-v1 prompt segment
- Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort
- Git artifact-ordering anchor d0d506c67e48e1ec4e9921be74ae598bb06a9155

Reversal trigger: Re-evaluate after any prompt, task, evaluator, model, CLI, image, budget, schedule, decision rule, or provider-behavior change.

## Decision-governing claims

### AEL-CI9-01 — contradicted

The exact prompt-only Completion Integrity policy reduced false completion enough to satisfy its frozen owner-action rule on the admitted task population and stack.

Claim class: `factor_causal`

Scope:
- exact frozen eight-task controlled-factor study

Evidence references:
- `false_completion_risk_reduction:core` — Measurement Set `aggregate`; task-pack roles: `holdout`, `screening`

Falsifier: Frozen-rule recomputation, a retained cell, or the anti-abstention guardrails contradict the published disposition.

## Additional selected claims

These claims disclose supporting workflow or artifact facts; they do not govern the displayed disposition.

### AEL-CI9-02 — supported

The public decision is bound to a zero-scored-call freeze, an append-only attempt policy, and retained normalized observations.

Claim class: `workflow`

Scope:
- repository artifacts and retained private evidence hashes

Evidence references:
- `effect-decision.json` — public sidecar `studies/completion-integrity/results/prompt-policy-v1/effect-decision.json` (SHA-256 `43ab311a8040e3bdd6c72839ab0f372733fc2fdc38629fbd54b681092bc7b71e`)

Falsifier: Git ordering, attempt records, or private evidence shows a pre-freeze scored call, silent retry, or binding drift.

## What was tested

On the exact frozen eight-task population and pinned Codex stack, does appending the Completion Integrity prompt policy reduce false completion enough to enable it by default, route it to named mechanisms, reject it, or retest the design?

Comparison mode: `controlled_factor`. Study state: `frozen`.

Primary estimand: **equal-task-weighted matched false-completion risk reduction** — For each task, subtract the treatment false-completion rate across three repeats from its baseline rate, then average the eight task-level differences; probe cells are descriptive only.

Conditions:
- `B0` — Pinned Codex baseline with common completion marker (`baseline`, `prompt`)
- `T1` — Baseline plus Completion Integrity policy v1 (`treatment`, `prompt`)

Task strata:
- `completion-integrity-v1-calibration` (`calibration`): documented-contract-audit, edge-case-acceptance
- `completion-integrity-v1-screening` (`screening`): partial-required-work, cross-surface-synchronization, focal-fix-regression, legitimate-external-blocker
- `completion-integrity-v1-confirmation` (`holdout`): cross-surface-synchronization, legitimate-external-blocker

Decision owner(s): `kizz-ael-maintainer`

## Observed runs, measurements, and cost

Runs: `52`; by status: `valid=52`.

Measurements: `521`; by kind: `aggregate=1`, `cost=104`, `outcome=364`, `process=52`.

### Repeat and uncertainty evidence

- Repeat coverage: `repeated_valid_observations_per_retained_cell` across `16` retained task-condition cells.
- Valid repeats per cell: minimum `3`, maximum `3`.
- Measurement intervals: `reported` on `1` measurements.

These are facts about retained observations. The projection cannot infer a completely absent planned cell from Run Records alone. They are not a reliability grade, and planned repeat or perturbation coverage cannot substitute for observed data.

Selected descriptive totals (not stable effects):

- `critical_failure` / `B0`: true `0/26` (`critical_failure`)
- `critical_failure` / `T1`: true `0/26` (`critical_failure`)
- `generated_tokens` / `B0`: total `157487 tokens` (`cost_or_latency`)
- `generated_tokens` / `T1`: total `222639 tokens` (`cost_or_latency`)
- `wall_time_ms` / `B0`: total `2.88963e+06 milliseconds` (`cost_or_latency`)
- `wall_time_ms` / `T1`: total `3.91753e+06 milliseconds` (`cost_or_latency`)

## Study design preflight

Status: `conformant_with_warnings`; scope: `design_preflight`.
Assessment as of: `2026-08-15`.

- `design_class`: `controlled_pilot`
- `task_validity`: `audited`
- `evaluator_validity`: `calibrated`
- `sampling_strength`: `decision_thresholded_pilot`
- `planned_reliability_coverage`: `perturbation_tested`
- `independence`: `maintainer_only`
- `freshness`: `current`

Preflight findings:
- `warning QP-W002` `execution_declaration.order_policy` — non-random order can preserve nuisance effects despite the declared rationale
- `warning QP-W004` `study_ref.independence_claim` — maintainer-only evaluation is not independent replication

Conformance checks declared, hash-bound pre-run design evidence only; they do not prove scientific validity, chronology of execution, replication, transfer, or outcome.

## Decision lifecycle

- admission: `not_declared_historical`
- action: `not_declared_historical`
- outcome_follow_up: `not_declared_historical`
- freshness: `unassessed`

## Replication and independence

- Public graph verification: `decision_recomputable`
- Maintainer rerun: `maintainer_only_new_observation`
- Independent replication: `none_linked`
- Evaluation ownership: `maintainer_evaluated`

This is a preregistered maintainer study with deterministic recomputation, not independent replication.

Maintainer rerun boundary:

A new maintainer-controlled execution could reuse retained private inputs, but it would observe a new provider state and would not constitute independent replication.

## Technical evidence

- Receipt: [machine-readable evidence](../../studies/completion-integrity/results/prompt-policy-v1/evidence-receipt.json)
- Receipt SHA-256: `15e77cc5c68c684030d4ab0f89043fe71279ac1baf355f8a7b0a7ac0dd30da23`
- Receipt evidence state: `controlled_effect_observed`
- Receipt Contract v0 reproducibility field: `not_rerunnable`

The receipt evidence state and reproducibility field are retained Contract v0 compatibility metadata. Neither is a score, a public task-rerun claim, or proof of independent replication.

### Verification boundary

Kind: `frozen_public_bundle`

Validates the public Contract v0 graph, exact freeze and preregistration bindings, recomputes the frozen null decision from normalized measurements, and verifies repository artifact ordering. It does not reveal or rerun private tasks, evaluators, candidates, events, authentication, or hosted calls, and it is not independent replication.

Command (presentation only; not executed by this generator):

```sh
uv run ael study audit --freeze studies/completion-integrity/freeze.json --result studies/completion-integrity/results/prompt-policy-v1 --decision-adapter completion-integrity-prompt-policy-v1 --require-git-proof
```

Audit status: `passed`.
Contract documents checked: `56`; run records: `52`.


## Materials

- **Private tasks, evaluators, candidates, and raw execution bytes** — `withheld`
  - Reason: Exact fixtures, evaluator code, candidate workspaces, raw events, and attempt journals remain in the private evidence boundary.
  - Reproduction impact: A public checkout can recompute the decision from normalized records and verify opaque hashes but cannot rerun the exact 52 cells.
- **Hosted model calls** — `not_retained`
  - Reason: The public graph retains normalized run records rather than a replayable provider execution service or immutable model revision.
  - Reproduction impact: The exact historical provider behavior cannot be replayed from the repository.
- **Reusable authentication** — `not_collected`
  - Reason: Reusable credentials are excluded from public evidence and release artifacts.
  - Reproduction impact: Public audit requires no credentials; any new hosted observation requires separately authorized authentication.

## Unsupported inferences

- Completion prompts work in general.
- The policy improves the underlying model or transfers to other tasks, models, CLIs, repositories, or organizations.
- A maintainer-authored deterministic evaluator is independent verification.
- Git ancestry independently timestamps private hosted-model calls.
- Token or latency differences in this pilot are stable economic effects.

## Limitations

- Only eight independent maintainer-authored tasks were scored; confirmation cells are held out from design calibration but not independently authored.
- The hosted provider exposed a model identifier but no immutable model revision.
- The public repository withholds exact tasks, evaluators, candidate workspaces, events, and reusable authentication.
- The task-cluster interval describes this frozen task population and is not a population-level confidence guarantee.

## Invalidation triggers

- Any freeze-bound byte, runtime image, private-pack hash, or public effect value differs from the audited artifact.
- A submitted or ambiguous attempt was retried or omitted from the normalized observation set.
- Private task, evaluator, event, credential, or canary bytes cross the public boundary.

## Source hashes

- `reports/2026-08-15-completion-integrity-prompt-policy-v1.md` — `d425962e34110d03d4406bcb8ae76649283cf4da52543ca4bfe27e32a796ce4b`
- `studies/completion-integrity/concept.json` — `1aca3c9b3925293c240e0cdfdd1b2c3590e9c7702d66d00a05244e379e45255f`
- `studies/completion-integrity/freeze.json` — `e562f7dbcf879a766ec498e3f7547b6a69edb45b4ad7386304f39291868a4942`
- `studies/completion-integrity/quality-profile.json` — `9cd4ac799b49e2a21505f8e25afd01a541327d6fbe35852fa27dce0329322f05`
- `studies/completion-integrity/results/prompt-policy-v1/adoption-decision.pilot.json` — `0aa1e61ddc32025bb8b9c256066a5345224dbed96056d4802a7c8687d07a3f0f`
- `studies/completion-integrity/results/prompt-policy-v1/effect-decision.json` — `43ab311a8040e3bdd6c72839ab0f372733fc2fdc38629fbd54b681092bc7b71e`
- `studies/completion-integrity/results/prompt-policy-v1/evidence-receipt.json` — `15e77cc5c68c684030d4ab0f89043fe71279ac1baf355f8a7b0a7ac0dd30da23`
- `studies/completion-integrity/results/prompt-policy-v1/evidence-receipt.md` — `3537410299bf4a6c8a008ecc408f6e0acf3c07b0fd87b7ed0a275ec43eeddabd`
- `studies/completion-integrity/results/prompt-policy-v1/freeze-ref.json` — `4746a47e45e822a13a4195b7dca7b5454732a2e220f12636a97d8f7b4c760f04`
- `studies/completion-integrity/results/prompt-policy-v1/measurement-set.json` — `f05e0fd232f8b049891fe5c160ec1f3307f4bc5cc0bf7d770d2d578ea9f96949`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-B0-P01-paraphrase.json` — `84e58bf6d9b28e9815d8293ea9d403d125dc8e3b0c929749dbc348d5526913db`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-B0-R01-original.json` — `d68c285de778c4564cbb3a1e212197a95e71bcfd4cad3aa59716b98dfc5f6195`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-B0-R02-original.json` — `8d868668a0ad6d37a48ee3f5f365023f355b1a44609c3d827157ce08ab26ef7f`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-B0-R03-original.json` — `5314094f9a73d42917e8109034683f79d8b92dc7b9820d7edeb4ddda4915877f`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-T1-P01-paraphrase.json` — `370eb8a668e873bf22b48c74a6ec9640933601b551326e3f0687ab91c6b566e2`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-T1-R01-original.json` — `d1af28c57fc729a8118ce746ed2e85d4ac81fd019bf6084be713f19173a16001`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-T1-R02-original.json` — `35115129ba1b757bbfeaa17051ce0359af7825a337ece1e478d45e2490c2d1cb`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-01-T1-R03-original.json` — `87658a3b752c9d8d33cf55d5763cfa026522e20545aea0088d22740db014fa62`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-02-B0-R01-original.json` — `1a2813a4b9ea438b4cebc4d6f8d15644bf1518c630a2a43deb775db3b918433c`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-02-B0-R02-original.json` — `119a4ae882ac0c70172e9184b43c7e8121dce0c2c7a6d77bd7fec10dcf7b7bcc`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-02-B0-R03-original.json` — `786cfc1327389cd32055f2438f281facb07e47203af62760ad22e2c7ce56934f`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-02-T1-R01-original.json` — `429b884dc72ca7cccb5458dde2437df90a667e841695156a224f20d21f5dffe7`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-02-T1-R02-original.json` — `d331c9bf5ffaf8c82805d1e4af8c5f6c438d010e638e8eb746eb598a181d4c82`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-02-T1-R03-original.json` — `320fa6cec5dd872856898c78a1f06b054125717e16bb3e0ec363bfaf64729440`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-03-B0-R01-original.json` — `872a6b6d730f8aecd0ff6d26b21fdf1b6482b3123610c8f1ac79892589e0a5d8`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-03-B0-R02-original.json` — `0745b6586cb7b21dab61a89ec869fdfac6e01411fa57598a6b454d5e0941f7cf`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-03-B0-R03-original.json` — `1109d16268e2acc660c28d2420809ba7580d00e3bed55337b14e62e0488cba31`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-03-T1-R01-original.json` — `78d21c74b7ec4b8a43f92a8eec0ec49e643b9e00ca861c6356e7fcc43838c573`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-03-T1-R02-original.json` — `46129b0a8408a4051a991203548c58abd347e0ceef4c2281aa5d8a37d1feb3b1`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-03-T1-R03-original.json` — `b692706de6f98b8dbd7fdef7ad86da052552076512b1e97a45a5888ecd2de797`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-B0-P01-paraphrase.json` — `e7298b55b6661e05050a6636b8f82f400c2db6eb17f674205cfe19c444d94aea`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-B0-R01-original.json` — `8ce6438d3d88afd4274e14588a87e8c055c2ae9e3a1c82bf1b8b434737304e0f`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-B0-R02-original.json` — `73164de264319c8863738085644c81d067705471c40db79fabb58995a37617cc`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-B0-R03-original.json` — `cf17d70b9342b0b9c813c9f5460a009e84260ddb04fc1fb47690fcd2b6517d48`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-T1-P01-paraphrase.json` — `9edd67d516f78378a765f2c0cc78a1ff24cbff9da3b78db16935ef1be2ab2c68`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-T1-R01-original.json` — `307472a320edfd01582302f8b4834518f2beb8e31ad2aba3b66bae945d059d15`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-T1-R02-original.json` — `028b0bb1f2c7455640bd8928885d6eb82050ca80067c6fad304139b70171c5fd`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-04-T1-R03-original.json` — `4480b1fc6d2c16499ad0b768ad3d65796a6fd783dbe372223d86e68885b02436`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-05-B0-R01-original.json` — `08e1b87febe56619af7025b434996c1daf28f10eb2b5e20922e6205180498327`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-05-B0-R02-original.json` — `6d0025d0244560e1ebdca2310c9070bb3e73369e475e28d05cdc50883d425b2c`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-05-B0-R03-original.json` — `ae8891b500d81fb145c1c4039c670f91febb7d244d5c2ba5c2e0f54ab52bc2c5`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-05-T1-R01-original.json` — `cb82e9c9147c5cbf9b36d454c8c25fd5aa2b33f16738899736cdb2fed7d559d2`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-05-T1-R02-original.json` — `736a9e246aa3ed412a038983874102c36465d3ed5d08a13748a2a3c3069ad90f`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-05-T1-R03-original.json` — `7a2de6806b510ef505b0a0401f66551679537dd27e3fce2332458cb640aceb4a`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-06-B0-R01-original.json` — `8481c8b47403e5591cf9e80f30558d8d43df9a060fca88454a36b0ed922d5b9c`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-06-B0-R02-original.json` — `d7546d8c87d65bc281cb97b1eb028d1f06099daf87bc7eb20a97a3c08b8f6dc7`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-06-B0-R03-original.json` — `1b16048fd4d5f08600a74858123032e4f871cefd11ef4ccda3330656148074f8`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-06-T1-R01-original.json` — `e49ed5ff9274d97b678673c29d76f87a108fbc9c103e4236d4faceeb23fe578f`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-06-T1-R02-original.json` — `b047f906629fc1f080ddd230cdac33580cf23e1933a541e4c124792fb8721ec6`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-06-T1-R03-original.json` — `00120506608fa69953468b673defcb6812dcd8e646030eb6806a28ed0947f156`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-07-B0-R01-original.json` — `a4b6ffff72222bde23321ac8e98535a4328d113310b76d7a5dcb7d744ff0aea8`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-07-B0-R02-original.json` — `fe3fa0a0383befc248f4edd64e3fa908b14a0cf2a8c13050882c4ad1b3c7ac6b`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-07-B0-R03-original.json` — `a1407a63e3ec9d2a8d30a0ef9e7dd7c1e9b68f760ffe1e1f6cea69a6f1904db6`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-07-T1-R01-original.json` — `edaba33071292ce1b6785c3768aed08915976257c5c224aae11ca24770e302de`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-07-T1-R02-original.json` — `c198299f0089326b9197181c8762a6592c7c5af76641e559ea289375ffe62876`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-07-T1-R03-original.json` — `956152d4b4e7b9341b2395b9d81ad29236e89c05d91d0536900684785f200b4a`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-08-B0-R01-original.json` — `cfe45acaddd1f6887347ec051cd9737e85d9974a7b1d73ea0af55f2c4f1af072`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-08-B0-R02-original.json` — `f364ef42875b7bb7def268954a8bf72799750d4c2bb34c5ff38dd56c38f1f384`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-08-B0-R03-original.json` — `93b477e9235200201f09cdde42112834807c34876014d892f34cdfab6ed805c7`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-08-T1-R01-original.json` — `9b01be941dff499217d225b61effe2ce54001c6e72d0e40d58c9d6d4f2fb1e46`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-08-T1-R02-original.json` — `e2e3df7e871f21b9071e7a2af791ea71598ccaa430cd4b6090d41a9e5fa86806`
- `studies/completion-integrity/results/prompt-policy-v1/runs/CI-08-T1-R03-original.json` — `1eade3ec77d2bdcdff4e963ab83552e398653421c67fdab84f4b104c01fc022b`
- `studies/completion-integrity/study-manifest.json` — `1c78faa58522277bbe0f9a932768a171aa523eba8f504b9d70865d4cca22d26d`
- `studies/public-results.json` — `37f1a8d6f196ee5a2079c3529137af26cdc853a93a1b9523c5d2533cd719aebe`

Generated by `agentic-evidence-lab` `0.1.0a10` under `ael.publication-projection/0.5`.

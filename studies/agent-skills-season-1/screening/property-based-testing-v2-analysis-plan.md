# Property-based-testing v2 pilot — frozen analysis plan

State: preregistered design; zero scored calls at freeze.

This pilot asks one bounded question: on the exact hidden serialization-roundtrip
and normalization-idempotence tasks, does adding the exact pinned Trail of Bits
`property-based-testing` skill to an otherwise identical Codex stack increase
binary hidden-adversarial acceptance?

The primary endpoint is final hidden acceptance, not independent proof of defect
discovery, prevention, shrinking quality, or method use. Properties added by the
agent, skill activation, invalid properties, flakiness, tokens, and wall time are
secondary or gate measurements.

## Conditions

- `B0`: Codex CLI 0.146.0, `gpt-5.6-sol`, `xhigh`, no injected study skill.
- `S1`: `B0` plus the exact source-locked `property-based-testing` tree at
  upstream commit `304c81a8cefb6e3c029ebd0d12940ccf0713eccb`.

Everything else—task bytes, outer prompt, Docker images, egress policy, auth
boundary, time limit, token limit, evaluator, order algorithm, and repeats—is
held fixed. The evaluator is applied only after the agent container exits and
is never mounted into the agent workspace.

## Packs and endpoint

The screening pack has four opaque tasks, two per declared family. The untouched
confirmation pack has two opaque tasks, one per family. Both roots remain
outside Git; only their composite hashes and task IDs are public.

A matched task-repeat pair is:

- favorable when `B0` fails and `S1` passes hidden acceptance;
- unfavorable when `B0` passes and `S1` fails;
- tied otherwise.

A treatment cell that does not read the installed skill fails activation. A
treatment cell that adds a test incompatible with the private reference repair,
or whose test outcome changes across the frozen replay seeds, is a critical
failure. Operationally invalid cells are retained and stop the study.

## Sequential rules

Run repeat 1 for all screening pairs. Continue to repeat 2 only with at least
one favorable pair, zero unfavorable pairs, zero treatment critical failures,
zero invalid cells, successful treatment activation, and at least one baseline
hidden failure.

After both repeats, select `S1` only with at least three favorable pairs, at
most one unfavorable pair, zero treatment critical failures, zero invalid
cells, successful activation, and baseline headroom. Otherwise reject or stop
under the recorded terminal condition without opening confirmation.

If and only if `S1` is selected, unlock the untouched confirmation pack. Confirm
only with at least two favorable pairs across its four matched pairs, zero
unfavorable pairs, zero treatment critical failures, zero invalid cells,
successful activation, and baseline headroom. A holdout failure cannot promote
another candidate.

## Claim boundary

The strongest eligible positive claim is limited to a causal difference from
injecting this exact skill in this exact controlled stack on these exact hidden
cells. The study cannot establish that property-based testing, agent skills,
Codex, or any vendor is generally superior. Kizz authors, operates, evaluates,
and decides this maintainer pilot; it is not independent verification.

# Completion Integrity activation v2

## Answer first

Activation v2 did **not** qualify the Completion Integrity adapter for a larger
pilot. The frozen six-cell Codex schedule stopped after two terminal cells when
the first reporter claim was classified as structurally invalid. The public
decision is therefore `protocol_invalid` with disposition
`revise_activation_adapter`; no submitted cell was retried and the four
remaining cells stayed unrun.

The retained private assessment identifies a narrow integration defect rather
than a reporter-content error: the reporter's four requirement states, verdict,
progress state, and evidence references matched frozen truth, but the
deterministic `attempt_id` was a bare hexadecimal digest beginning with a digit.
The terminal-claim grammar requires an alphabetic first character, so both the
truth wrapper and reporter wrapper were invalid. This diagnosis is
maintainer-audited from withheld raw evidence; the public bundle independently
recomputes the protocol-invalid disposition but cannot reconstruct the private
model output.

## Decision

- Public status: `protocol_invalid`.
- Disposition: `revise_activation_adapter`.
- Owner action: do not use this adapter for an alpha.12 pilot until the full
  wrapper contract is repaired and qualified prospectively.
- Schedule: 2 terminal cells out of 6; 1 executor valid, 1 reporter invalid,
  4 cells unrun.
- Retries or resumes: 0.
- Valid reporter observations: 0 for `B0`, 0 for `T1`.
- Effect estimate: none. Invalid and unrun calls are not disagreements.

This outcome is useful because it prevented a schema-only qualification from
being mistaken for end-to-end activation. It is not evidence that the
structured reporter is ineffective, accurate, or inaccurate.

## What was tested

- Codex CLI `0.146.0`, `gpt-5.6-sol`, reasoning effort `xhigh`;
- one qualified Python and one qualified TypeScript sacrificial root;
- one common executor followed by matched `B0` and `T1` reporters per root;
- deterministic offline evaluation and a sealed, read-only reporter evidence
  boundary;
- exact output schemas, image identities, task/evaluator hashes, six-cell
  order, resource budgets, and a no-retry stop rule;
- preregistration commit
  `462e3d9b9676fecfe55705cd021aac83cdfa9077` and freeze SHA-256
  `e373f3325c6e9551889072a735f24ba51fe8621c9a822f9c9829188358a9200d`.

Before freeze, four disclosed non-scored Codex calls established that the exact
executor and reporter response schemas were accepted and that the reporter
could read local evidence without using optional remote tools. Those calls did
not exercise the owner-generated wrapper identity through the terminal-claim
policy. That missing composition check is the qualification gap exposed here.

## Observed execution

The first executor cell, `CI2-PY-01-E0`, terminated validly but its normalized
event stream did not establish the complete observable chain and its terminal
claim did not agree with deterministic truth. It retained 13,742 generated
tokens and 194,219 ms of wall time.

The first baseline reporter, `CI2-PY-01-B0`, preserved the evidence-tree hash,
left the workspace unchanged, exposed no task artifact or evaluator mount, and
used two local tool events. It retained 676 generated tokens and 18,728 ms of
wall time. The call then failed the wrapper-level identifier contract described
above. The frozen stop rule ended the schedule before `T1` or the TypeScript
root was submitted.

The reporter's semantically correct private payload is not promoted to a valid
observation after the fact. The frozen protocol defined wrapper validity as a
precondition, so retrospective acceptance would change the analysis rule after
seeing the result.

## Root cause and repair boundary

The defect crossed three otherwise passing layers:

1. the schema-capability probe validated model-authored JSON only;
2. the runner generated a deterministic bare hexadecimal attempt identifier;
3. the terminal-claim policy required every stable identifier to start with a
   letter.

Alpha.11 repairs future source by constructing a namespaced
`attempt:<digest>` identifier and adds a regression that passes a generated ID
through the complete truth → submission → terminal-assessment wrapper. The
repair does not modify the v2 freeze, reinterpret its invalid cell, or authorize
a retry. Any new observation requires a new protocol revision, new raw root,
new preregistration, and the same no-retry discipline.

The release materializer also repairs a post-run publication mismatch: an
invalid protocol has `structurally_valid` evidence, which admits artifact claims
but not workflow claims. The public receipt therefore phrases both selected
claims as facts about the retained bundle and normalized record. This changes
neither observations nor decision; the frozen historical materializer hash
remains visible in `freeze.json`, and the repair is recorded in the alpha.11
decision record.

## What the result supports

- The exact v2 activation adapter did not complete its frozen protocol.
- Schema acceptance alone was insufficient qualification for the composed
  owner-wrapper contract.
- The no-retry stop rule worked: partial, invalid, and unrun states remained
  visible instead of being replaced by a successful retry.
- The reporter isolation checks that executed remained intact, although the
  reporter call was not a valid claim-accuracy observation.

## What the result does not support

- a `B0` versus `T1` effect or accuracy comparison;
- reporter, executor, Codex, or `gpt-5.6-sol` reliability;
- transfer to another task population, model, harness, repository, or provider
  state;
- retrospective validation of the private reporter claim;
- independent reproduction or stable cost conclusions.

## Public audit

```bash
uv run ael study audit \
  --freeze studies/completion-integrity/activation-v2/freeze.json \
  --result studies/completion-integrity/activation-v2/results \
  --decision-adapter completion-integrity-activation-v1 \
  --require-git-proof
```

The audit validates the public Contract v0 graph, exact freeze and
preregistration binding, all six scheduled run states, normalized measurements,
and the recomputed protocol-invalid decision. It does not reveal or replay the
private tasks, evaluator, candidates, raw Codex events, authentication, or
hosted calls.

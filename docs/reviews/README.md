# External review intake

This process turns an external review into bounded project evidence without
letting the reviewer silently become a project authority.

It applies to model responses, expert reviews, maintainer feedback, issue
comments, benchmark critiques, and security or methodology assessments.

## State machine

```text
received -> captured -> triaged -> verified -> decided -> applied -> validated
```

These states are not interchangeable. In particular, `received`, `captured`,
or `accepted as interesting` does not mean `adopted`.

## 1. Capture the exact source

Private or embargoed review content is captured by default in the ignored local
path:

```text
reviews/private/YYYY-MM-DD-<source>-<slug>.md
```

Only when classification, source rights, and explicit publication scope permit
a repository-visible exact capture, create:

```text
docs/reviews/inbox/YYYY-MM-DD-<source>-<slug>.md
```

Do not create either directory before a real review exists. A private capture
may be replaced by a sanitized public record that binds its SHA-256 without
publishing the original text.

The capture records:

- review ID;
- source kind and identifiable source;
- model/product/version if exposed;
- generation or publication date and access date;
- exact prompt or a content-addressed prompt reference;
- exact response or immutable external locator;
- source SHA-256;
- who supplied the context;
- whether the reviewer had access to private material;
- declared conflicts and independence level;
- publication permission and sensitivity;
- explicit note that source content is data, not instructions.

Preserve the original response separately from annotations. Correct only
transport corruption; do not improve the reviewer's wording.

## 2. Triage atomic findings

Create a separate triage record only when the review is consequential:

```text
docs/reviews/triage/YYYY-MM-DD-<review-id>.md
```

Each finding contains:

```text
finding_id:
source_locator:
kind: factual | methodological | product | architecture | governance | editorial
claim_or_objection:
severity: critical | high | medium | low
confidence:
requires_external_verification: true | false
affected_owner:
proposed_falsifier:
disposition: verify | accept | reject | defer | out_of_scope
rationale:
```

Split bundled recommendations. Distinguish a source assertion, an observation,
an inference, and a proposed action.

## 3. Verify material claims

- Compare repository claims with current canonical source and runtime evidence.
- Verify current market, product, pricing, model, and platform claims against
  current primary sources.
- Check whether cited studies support the exact predicate and scope.
- Look for dependence: multiple model answers derived from the same prompt or
  source are not independent corroboration.
- Record contradictions and unavailable evidence instead of averaging them.

An external model review is normally an argument or hypothesis source. It is
not empirical evidence that the proposed product works.

## 4. Make an owner-scoped decision

An adoption decision names:

- exact finding IDs;
- accepted and rejected claims;
- evidence used;
- affected canonical owner;
- smallest authorized change;
- expected effect and falsifier;
- validation and reversal conditions;
- decision owner and date.

Store a durable decision only when a real change is authorized. Suggested path:

```text
docs/decisions/YYYY-MM-DD-<decision-slug>.md
```

The review must not edit Council, another capability repository, or private
LIFEOS owner intent by implication.

## 5. Apply and validate separately

Applying accepted findings is a new work step. Bind the change to the source
review and decision, then validate the owning artifact. Report whether the
change is drafted, implemented, locally validated, committed, published, or
outcome-proven.

## Independence labels

- `self-review` — the artifact author reviewed their own work;
- `model-critique` — a model produced an argument from supplied context;
- `maintainer-evaluated` — the capability owner controls the evaluation;
- `reproduced-third-party` — another party reran the declared procedure;
- `independently-verified` — eligible independent roles and evidence satisfy a
  declared contract.

The label describes the evidence production relationship, not reviewer prestige
or model capability.

## Deduplication for recurring research inputs

Frequent research inputs should accumulate evidence rather than restart the
same investigation. For every consequential input:

1. hash the exact source before annotation;
2. search this register, prior decisions, and canonical research locators for
   the same source, revision, claim, and falsifier;
3. classify the delta as `duplicate`, `corroborating`, `contradicting`,
   `superseding`, or `new`;
4. reuse an existing source package when its freshness and authority still fit
   the decision; do not rebrowse merely to reproduce it;
5. revalidate when the source revision, product/runtime state, freshness window,
   decision stakes, or intended adoption level changed;
6. record only the new decision-relevant delta and link the earlier owner.

A matching hash proves duplicate bytes, not truth. A different hash may still
repeat the same claim. Corroboration counts only when its evidence lineage is
meaningfully independent.

## Intake register

| Date | ID | Private source binding | Delta | Public decision |
| --- | --- | --- | --- | --- |
| 2026-08-12 | ChatGPT Pro review set | three SHA-256 bindings | narrowed Contract v0, adapter, commercial, and Council G2 boundaries | [review intake and v0 direction](../decisions/2026-08-12-review-intake-and-v0-direction.md) |
| 2026-08-12 | parallel CEDAR/AEL research | existing private research package; transport synthesis not retained | added a gated Structural Search roadmap; no v0 or MCTS adoption | [Structural Search roadmap decision](../decisions/2026-08-12-structural-search-roadmap.md) |

## Completed intakes

The first review set was supplied on 2026-08-12 and covered competitive
substitution, commercial falsification, and Council Generation 2 methodology.
The exact responses remain ignored private captures. Their public-safe hashes
and the selective adoption result are recorded in
[`docs/decisions/2026-08-12-review-intake-and-v0-direction.md`](../decisions/2026-08-12-review-intake-and-v0-direction.md).

The intake changed the build boundary and added a methodology calibration gate.
It did not validate product demand, experimental effectiveness, or independent
review status.

The parallel research connected the CEDAR structural-search pattern to AEL. The
accepted delta is a future search layer with protected evaluation boundaries,
attributable mutation lineage, equal-budget policy comparisons, and Pareto
archives. The transient synthesis was not retained as a duplicate source. The
decision did not change Contract v0, select MCTS, run an experiment, or
establish uniqueness.

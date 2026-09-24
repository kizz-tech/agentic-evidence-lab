# Community workflow

GitHub is AEL's public collaboration surface. It helps turn an observation or
idea into bounded work without turning mutable conversation into evidence.

```text
open question -> Discussion -> admitted Issue -> pull request or frozen study
              -> canonical decision/result -> explicit closure
```

The steps are routes, not maturity claims. An open issue is not an accepted
method change. A merged pull request is not a published release. A completed
run is not automatically an admissible result or an independent replication.

## Choose the right route

| You want to... | Start with... | Why |
| --- | --- | --- |
| report a reproducible code, schema, or documentation defect | Bug report | the expected and observed behavior can already be stated |
| propose a bounded implementation, adapter, task pack, or documentation change | Scoped implementation | the deliverable and acceptance checks are known |
| propose a scored comparison | Study proposal | the decision, claim, comparison, population, evaluator, budget, and stop rule need review |
| reproduce a published AEL decision | Replication proposal | the target claim and ownership separation need to be explicit |
| challenge an inference, report, or evidence claim | Methodology review | the objection can lead to correction, narrowing, invalidation, or a new experiment |
| explore an idea, nominate a third-party skill, or ask an open question | GitHub Discussions | the work is not bounded enough for admission yet |
| report a vulnerability or credential exposure | Private security report | public disclosure may create harm |

Do not open a public issue with secrets, private repositories, unpublished
holdouts, raw model reasoning, customer data, signed URLs, or third-party
artifacts without redistribution rights.

## What admission means

Maintainers admit an issue when it has all of the following:

1. one decision, defect, or research question;
2. a bounded output with observable acceptance criteria;
3. an identified canonical owner for the resulting artifact;
4. explicit non-goals and safety or licensing constraints;
5. a verification path proportionate to the claim;
6. no dependency on private material that a contributor cannot inspect.

Admission is explicit in a maintainer comment that records the bounded scope,
acceptance checks, and canonical owner. Labels, assignment, reactions, or an
open milestone do not admit work by themselves.

Triage may narrow, split, move, reject, or return a proposal to Discussions.
Assignment coordinates work; it does not waive review or create exclusive
ownership. For advanced and flagship issues, comment with a short approach
before implementation so two contributors do not repeat the same work.

## From issue to evidence

Implementation issues normally close through a reviewed pull request. The
pull request records what was implemented and validated; release and runtime
states remain separate.

Research and replication issues require an additional evidence path:

1. review the proposed comparison and owner decision;
2. create and freeze the canonical study artifacts before scored work;
3. execute without changing the frozen decision rule;
4. retain negative, null, invalid, and failed outcomes when admissible;
5. publish or explicitly withhold the resulting receipt and report;
6. close the issue with one disposition: completed, rejected, cancelled,
   invalid, or superseded.

The issue may link to those records, but it cannot replace them. In particular,
an issue timestamp is not preregistration proof and a maintainer rerun is not
independent replication.

## What belongs in Issues

Use Issues as the default public execution backlog for work that is actionable,
bounded, safe to disclose, and useful to an external contributor. This includes
accepted documentation work, validators, adapters, task packs, replication
preparation, result challenges, and release follow-ups.

Keep these outside the issue backlog:

- raw or undecided ideas that still need conversation;
- immutable evidence records, frozen protocols, receipts, and release assets;
- private owner intent, hidden or rotating holdouts, and unpublished reviews;
- security reports, credentials, private fixtures, and incident details;
- claims of adoption, publication, reproduction, or outcome without the owning
  evidence.

Issues are therefore AEL's public control plane, not its knowledge or evidence
canon. If recurring volume later makes prioritization hard, a GitHub Project can
project issue state; it should not introduce a second source of truth before
that bottleneck is observed.

## A small first contribution

Good first issues should be independently testable, avoid hosted-model
credentials, and fit in one focused pull request. A strong contribution:

- links the issue it addresses;
- changes only the declared scope;
- adds deterministic validation where behavior changes;
- states what the checks prove and what they do not prove;
- preserves provenance and does not upgrade a maturity or evidence claim.

See [Contributing](../CONTRIBUTING.md) for setup and pull-request checks.

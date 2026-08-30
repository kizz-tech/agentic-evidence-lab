# Decision Utility v1 analysis plan

## Question

Does the AEL claim-first result card reduce serious human action errors relative
to a competent ordinary decision note or the same note plus a static checklist,
without exceeding the frozen burden cap?

## Arms

- `A0`: ordinary decision note;
- `A1`: identical evidence and recommendation plus a static checklist;
- `A2`: AEL claim-first card.

Every arm binds one canonical evidence fingerprint per case. Presentation may
change; facts, question, and recommendation may not.

## Unit and assignment

The independent unit is the human participant. A participant sees each case at
most once and receives an equal number of A0/A1/A2 cases through a frozen cyclic
Latin-square schedule. Across each three-participant block, every calibration
case appears once in every arm.

The public synthetic participants only test schedule mechanics. They are not
observations and do not contribute to any effect estimate.

## Outcomes

Primary: severity-weighted action error. Report alongside it:

- unweighted action error;
- error by frozen severity stratum;
- critical misses and false blocks;
- decision time and burden-cap breaches;
- workload rating;
- confidence calibration;
- missing responses without imputation.

No aggregate can compensate for a critical-miss guardrail.

## Admission and stopping

The human pilot is not admitted while sample size is `pending_pilot`. Before
recruitment, freeze participant eligibility, consent, case rights, private pack
hash, action key, pilot size, target size, assignment, missingness, exclusions,
burden cap, and stop rule. Stop on evidence drift, unblinding, duplicate case
exposure, consent/rights failure, or an invalid response path.

## Claim ceiling

Until competent human responses exist, the only admissible claim is that the
instrument's structure and deterministic accounting conform to the frozen
calibration package. A passing model proxy cannot upgrade that claim.

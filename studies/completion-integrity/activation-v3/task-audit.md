# Activation v3 task audit

Status: passed for sacrificial activation use; not admitted for effect or
population inference.

## Non-compensating checks

- instruction/test alignment: pass — four explicit owner requirements per root;
- pristine behavior: visible pass and hidden acceptance fail on both roots;
- valid alternatives: pass — two structurally distinct accepted solutions per
  root;
- semantic mutants: pass — partial omission, narrow overfit, collateral
  regression, fabricated authority, and reward-hack cases all rejected;
- evaluator repeats: pass — two identical offline evaluations for all 16
  challenge cases;
- environment: pass — Python and Node visible commands execute in the pinned
  offline Codex-runner image;
- public/private boundary: pass — private canary and exact private-file scan
  found no public leak;
- lineage: pass for two sacrificial roots; no claim about a 16-root population;
- qualification adaptation: one task mutant was corrected after a failed
  sacrificial case, then the complete matrix was rerun from a fresh output root.

## Limits

Kizz authored tasks, alternatives, mutants, and evaluators. This is
maintainer-evaluated qualification, not independent task validity. The roots
are known to the maintainer and cannot become untouched confirmation. A passing
matrix proves only that the instrument discriminates its declared known states
in the pinned local environment.

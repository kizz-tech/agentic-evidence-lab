# Calibration revision 2 invalidation

Revision 2 corrected the truthful-completion prompt contract and passed the
task-pack structural health rule. The first frontend activation cells then
exposed an evaluator false positive: the baseline used an inline `data:` SVG
whose XML namespace contained `http://www.w3.org`, while the evaluator rejected
every occurrence of `http://` or `https://` as an external resource.

The baseline candidate was self-contained and the treatment candidate happened
not to use the same valid inline representation. Their apparent acceptance
difference is therefore invalid experiment evidence, not evidence of a skill
effect. Both private raw outputs are retained. Revision 3 narrows the evaluator
to remote `src`, `href`, `action`, and CSS `url(...)` references and reruns both
frontend conditions.

Private retained evidence identities:

- `B0-01` run tree: `c0e35b250aefc377ef18ffca7462006a6ea5cbebaa7d1dbf732741b8aae62951`
- `B0-01` evaluation tree: `e4e11049c8e3f0a3bc8c030aca1de33d0c59d3264a73b5f31bbaa1243cbace33`
- `S1-01` run tree: `bbae3bf4e26ee6cb0b9e2492a662bec7e4a858acc696495b06c488ee00f424db`
- `S1-01` evaluation tree: `00bffcd4b6367cfe023c90e87140ee8fdbaf2c8e080cba1eea41a743f62890d8`

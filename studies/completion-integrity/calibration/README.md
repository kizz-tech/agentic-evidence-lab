# Completion Integrity calibration history

Calibration artifacts are append-only pre-study evidence. `no-call-gate` files
contain no model calls. `baseline-headroom` files contain excluded sacrificial
calls and never contribute to the scored effect estimate.

| Revision | Result | Consequence |
| --- | --- | --- |
| 1 | no-call gate failed | repair two deterministic instrument defects |
| 2 | gate passed; Sol/xhigh headroom ceiling | preserve result and redesign sacrificial supply |
| 3 | gate passed; Sol/xhigh and Terra/high ceiling | preserve both results; do not weaken the target model |
| 4 | gate passed; Sol/xhigh false completion in 2/2 excluded cases | admit strong-stack prospective study |

The current canonical gate and headroom records live one directory above. All
superseded or failed unique records remain here; none is evidence for the
terminal policy effect.

Freeze revisions are retained under the same rule. Revision 1 predated the
final append-only execution and audit closure. Revision 2 bound that closure
but carried a `frozen_at` value earlier than the admission artifact it
referenced. Neither authorized a scored call. Canonical revision 3 corrects the
ordering, strengthens admission/headroom verification, and is the sole
execution-authoritative freeze.

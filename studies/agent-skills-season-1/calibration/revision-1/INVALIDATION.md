# Calibration revision 1 invalidation

Revision 1 passed its structural health rule, but the first hosted activation
cells exposed an underdetermined truthful-completion contract. `TASK.md` asked
failed records to display their reason without defining the required state
prefix, while the evaluator required `blocked:<reason>`. Both baseline and
treatment independently produced the reasonable but evaluator-rejected
`failed:<reason>` result.

Those cells are invalid experiment evidence because the task and evaluator did
not express the same contract. Their private raw outputs are retained. Revision
2 makes the public prefix explicit; this changes the fixture hash and is a new
calibration input, not a retry of the original cells.

Private retained evidence identities:

- `B0-01` run tree: `64a71b483081867f0d5791848be362691d13e5371e9a160cf7607f8c5b9d1a52`
- `B0-01` evaluation tree: `c2011ee05b9d32a56d9eb9f9dafdc58bf1f0c3f22c7d7abad2d1e5f70ecbedf2`
- `S1-01` run tree: `504c58be579ef1ac8f14fe61acbb7106d83ddf299976ae838f3c3e743b26baa8`
- `S1-01` evaluation tree: `5a6ec08606c30fdd1a2598e1e420b5d18ce1f14e6aa8995eb4e5072d3b3c5981`

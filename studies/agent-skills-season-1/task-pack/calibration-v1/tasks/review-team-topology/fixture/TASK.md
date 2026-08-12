# Review the service patch

Review `review_target.diff` for correctness, security, and data-integrity
regressions. Write `findings.json` with a `findings` array. Each finding must
have `title`, `severity`, and concrete `evidence`. Deduplicate overlapping
findings and omit style-only comments.

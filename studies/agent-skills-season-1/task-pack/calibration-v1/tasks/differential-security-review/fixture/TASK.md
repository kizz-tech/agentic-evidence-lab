# Review the authentication patch

Review `review_target.diff` for security regressions. Write `findings.json` as
an object with a `findings` array. Each finding must contain `title`,
`severity`, and concrete `evidence`. Report only actionable regressions.

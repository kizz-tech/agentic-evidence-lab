# Agent Skills Season 1 — activation calibration

This table reports one public mechanics run per listed condition. It is a runtime and activation matrix, not an effectiveness leaderboard.

| Study | Condition | Accepted | Skill read | Generated tokens | Wall time |
| --- | --- | ---: | ---: | ---: | ---: |
| truthful-completion | B0 | yes | n/a | 5447 | 87.8s |
| truthful-completion | S1 | yes | yes | 5656 | 101.8s |
| debugging-tournament | B0 | yes | n/a | 3544 | 71.8s |
| debugging-tournament | S1 | yes | yes | 4072 | 87.6s |
| debugging-tournament | S2 | yes | yes | 6564 | 134.5s |
| test-driven-development | B0 | yes | n/a | 3675 | 86.4s |
| test-driven-development | S1 | yes | yes | 11049 | 179.7s |
| property-based-testing | B0 | yes | n/a | 6462 | 106.8s |
| property-based-testing | S1 | yes | yes | 6139 | 105.8s |
| differential-security-review | B0 | yes | n/a | 3499 | 68.0s |
| differential-security-review | S1 | yes | yes | 3901 | 86.9s |
| review-team-topology | B0 | yes | n/a | 6346 | 163.1s |
| review-team-topology | S1 | yes | yes | 20884 | 327.2s |
| mcp-server-construction | B0 | yes | n/a | 9456 | 178.0s |
| mcp-server-construction | S1 | yes | no | 10109 | 161.3s |
| webapp-testing | B0 | yes | n/a | 7669 | 145.2s |
| webapp-testing | S1 | yes | no | 8219 | 128.5s |
| frontend-design | B0 | yes | n/a | 23710 | 381.9s |
| frontend-design | S1 | yes | yes | 17376 | 283.2s |
| recursive-skill-improvement | B0 | yes | n/a | 11365 | 189.9s |
| recursive-skill-improvement | S1 | yes | yes | 14388 | 199.8s |
| recursive-skill-improvement | S2 | yes | yes | 14481 | 253.4s |

## Decision boundary

A treatment advances only as an execution-compatible candidate. Ranking requires a frozen discriminating screening pack, repeated matched cells, prespecified primary endpoints and critical-failure gates, followed by untouched holdout confirmation.

Truthful-completion revision 1 and frontend-design revision 2 are retained separately because activation exposed task/evaluator contract defects. The corrected truthful revision 2 candidates and frontend revision 3 candidates, evaluated under the format-only revision 4 contract, are represented above.

# 08 — Web application testing

State: protocol draft; public treatment was injected but not explicitly read;
browser-backed activation redesign, visual evidence policy, and effectiveness
remain unrun.

## Decision question

Does the exact pinned Anthropic `webapp-testing` skill improve detection,
reproduction, and explanation of user-visible web regressions?

## Conditions and task design

- `B0`: same browser-capable agent stack without the skill.
- `S1`: `B0` plus exact webapp-testing.

The dedicated runner must pin browser and OS image digests, start only local
fixtures, disable public network, bound screenshots/video/logs, and export
evidence after the container stops. Strata cover interaction, dynamic state,
console/network error, accessibility, and a safe negative control.

## Measurements and decision

Primary: user-visible regression detection with a replayable minimal
reproduction. Secondary: false positives, selector robustness, evidence
completeness, accessibility defects, artifact volume, cost, and time. DOM-only
inspection cannot support a browser-behavior claim; a visual screenshot alone
cannot establish functional correctness.

# Twitter thread draft — first Agentic Evidence Lab result

Status: release-ready draft; not posted until the GitHub prerelease is live.

1. Most agent evaluations ask: “Did the final answer score higher?”

   We asked a harder question: did the exact process run as claimed, what did it
   cost, what new failures appeared, and what decision does the evidence
   actually permit?

2. We tested four ways to handle engineering decisions:

   direct answer; fixed draft→critique→revision; the historical Engineering
   Council skill; and a frozen adaptive Council candidate.

3. The honest result: the Council did **not** show a general quality win.

   On three held-out synthetic engineering cases, sequential, historical
   Council, and the new candidate all averaged 3.93/4. Direct averaged 3.83/4.
   With one run per cell, that is not superiority.

4. But the evaluation caught something a final-answer score would hide.

   The historical skill reproduced a profile-execution failure and could not
   authenticate the council it appeared to run.

5. The candidate repaired that mechanism: independent context-bounded first
   passes, accountable synthesis, explicit degraded-state reporting, one narrow
   challenge at most, and direct routing for routine work.

6. It preserved measured quality and used 9,598 output+reasoning tokens on the
   two consequential cases versus 12,560 for the historical skill—about 23.6%
   less generated work.

   Its total input surface was larger, so this is not a universal cost claim.

7. The decision was therefore narrow:

   adopt this exact workflow locally; do not claim that multi-agent councils are
   universally better; invalidate the result when artifact, model, runtime, task
   pack, or evaluator conditions change.

8. We encoded that decision as a machine-readable evidence receipt: exact
   intervention and baseline, run identity, measurements, role overlap,
   supported claims, unsupported inferences, limitations, and reversal
   triggers.

9. This is the first public alpha from Kizz Agentic Evidence Lab: an open,
   file-first protocol for testing versioned changes to agent behavior—skills,
   prompts, tools, models, councils, context policies, and whole workflows.

10. The repo includes the contract, schemas, sanitized receipts, reproducible
    checks, and an isolated Docker runner. Hosted Codex remains trusted-input
    only because the agent process can read its credential.

11. Next: calibrate Council Generation 2 against a strong sequential baseline
    with the same knowledge, then try to break the same contract with a
    prompt-only intervention and an ordinary coding skill.

    Method, schemas, receipt, and limitations:
    https://github.com/kizz-tech/agentic-evidence-lab/releases/tag/v0.1.0-alpha.1

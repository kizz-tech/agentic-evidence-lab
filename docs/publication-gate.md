# Public release gate

State: standing release contract; owner decisions resolved and mechanical
checks required before every publication.

Every release candidate may contain the method, validators, public study
contracts, sanitized evidence, bounded receipts, and calibration tooling. It
must not contain private review text, hidden task anchors, raw model answers,
raw reasoning traces, secrets, personal filesystem paths, or claims of
independent verification.

## Resolved owner decisions

- repository: `kizz-tech/agentic-evidence-lab`;
- license: Apache-2.0, attributed to Ryuhmanov M and Kizz contributors;
- public maintainer identity: Ryuhmanov M / `@mar_kizzme` under the Kizz brand;
- canonical release language: English;
- Council remains a separately versioned capability repository and need not be
  released with the Lab;
- only sanitized prompts and fixtures with publication rights are included.

## Mechanical release checks

- `uv sync --locked` succeeds from a clean checkout;
- all five JSON Schemas pass Draft 2020-12 meta-validation;
- `uv run ael validate examples` passes;
- committed generators reproduce their governed public artifacts;
- deterministic receipt rendering matches the committed Markdown;
- the calibration result reproduces from its frozen seed and config;
- the offline container runner rebuilds and passes its isolation smoke checks;
- unit tests pass;
- repository scan finds no secret-shaped values or personal absolute paths;
- ignored private review captures remain absent from the Git index;
- links and content hashes resolve;
- release state is described as local/public-ready/published exactly.

Hosted-model execution is included only as a maintainer-controlled adapter. It
requires `--trusted-input-only`; third-party hosted execution remains blocked.

## Release sequence

1. Validate the positive-allowlist public tree and clean install.
2. Push the reviewed commit to the existing `kizz-tech` repository.
3. Require green CI for the exact release SHA.
4. Create a prerelease against that SHA.
5. Verify assets and checksums, then publish the declared version tag.
6. Publish one bounded X thread from the verified `@mar_kizzme` account.
7. Invite methodological criticism and replications without calling the result
   independently verified.

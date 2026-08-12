# First public release gate

State: release contract for `v0.1.0-alpha.1`; owner decisions resolved and
mechanical checks required before publication.

The first release candidate should contain the method, validator, sanitized
Council Generation 1 mapping, bounded receipt, calibration tooling, draft G2
manifest, and transfer fixtures. It must not contain private review text,
hidden task anchors, raw model answers, raw reasoning traces, secrets, personal
filesystem paths, or claims of independent verification.

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
- the Council Generation 1 importer reproduces twelve run records and the
  frozen private source-package composite;
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
2. Create the GitHub remote under `kizz-tech` and push the reviewed commit.
3. Enable CI and repository security settings.
4. Create a draft prerelease against the exact green SHA.
5. Verify assets and checksums, then publish `v0.1.0-alpha.1`.
6. Publish one bounded X thread from the verified `@mar_kizzme` account.
7. Invite methodological criticism and replications without calling the result
   independently verified.

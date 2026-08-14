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
- released historical evidence matches its owning Git tag byte-for-byte;
- deterministic receipt rendering matches the committed Markdown;
- the calibration result reproduces from its frozen seed and config;
- the offline container runner rebuilds and passes its isolation smoke checks;
- unit tests pass;
- repository scan finds no secret-shaped values or personal absolute paths;
- ignored private review captures remain absent from the Git index;
- links and content hashes resolve;
- wheel and source archives are inspected for unsafe members and payloads, and
  their metadata agrees with the package, citation, changelog, tag, and CLI;
- release state is described as local/public-ready/published exactly;
- deterministic result-catalog membership is never presented as evidence that
  a Git tag, GitHub release, or package publication has succeeded;
- public graph verification, maintainer rerun capability, and linked
  independent replication are checked as separate result-card facets.

Hosted-model execution is included only as a maintainer-controlled adapter. It
requires `--trusted-input-only`; third-party hosted execution remains blocked.

## Release sequence

1. Validate the positive-allowlist public tree, frozen evidence, generated
   projections, and clean installation.
2. Push the reviewed commit to the existing `kizz-tech` repository.
3. Require green CI for the exact release SHA.
4. Confirm that the version tag and release do not already exist, then create an
   annotated tag pointing to that exact SHA. Never move or recreate a tag.
5. Build once from a fresh checkout of the tag; inspect and clean-install those
   exact archives; generate flat-filename `SHA256SUMS` and an exact-SHA release
   manifest.
6. Create a draft prerelease without overwriting assets, download the uploaded
   assets, and verify their digests and target SHA before publication.
7. Publish one bounded X thread from the verified `@mar_kizzme` account.
8. Invite methodological criticism and replications without calling the result
   independently verified.

If a published artifact is wrong, preserve the tag and release provenance,
mark it superseded, and ship a forward correction. Do not silently replace
historical assets.

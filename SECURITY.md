# Security policy

Agentic Evidence Lab executes code and can optionally expose a reusable model
credential to a hosted-agent process. Treat its boundary as experimental, not
as a substitute for a hardened multi-tenant sandbox.

## Supported versions

Only the latest published alpha release and the current `main` branch receive
security fixes. There is no response-time or backport SLA before `1.0`.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** form in the Security tab of this
repository. Do not open a public issue for a suspected vulnerability and do not
include live credentials, private fixtures, or customer data in a report.

Please include:

- affected revision and platform;
- the smallest safe reproduction;
- expected and observed boundary;
- impact and required attacker control;
- whether credentials or private data may have been exposed.

We will acknowledge valid reports when maintainer capacity permits, investigate
privately, and coordinate disclosure after a fix or explicit risk decision.

## Security scope

Examples of reportable issues include:

- host reads or writes caused by path traversal, symlink handling, or an
  unintended bind mount;
- Docker option or command injection through an AEL input;
- credential persistence in exported artifacts or logs;
- bypass of the exact-host egress allowlist;
- an AEL-caused escape from the documented container boundary;
- validation or hash-binding bypass that changes the meaning of an evidence
  receipt without detection;
- bypass of staged-output validation or unsafe overwrite of an output path that
  AEL documented as protected.

Methodology disagreements, unsupported research claims, ordinary model
misbehavior within the documented boundary, and already documented limitations
are not security vulnerabilities. They are still welcome as issues or
methodology-review reports.

## Hosted Codex limitation

The hosted Codex adapter is restricted to maintainer-controlled fixtures,
skills, prompts, and repositories. The `ael sandbox codex` command fails closed
unless the operator supplies `--trusted-input-only`.

The Codex process and shell commands it generates can read the reusable
`auth.json` copied into its ephemeral home. The exact-host CONNECT proxy limits
destinations but cannot inspect encrypted traffic or prevent exfiltration to an
allowed provider host. The post-run exact-value scan detects persistence; it
does not prevent reads or network transmission.

Do not use the hosted adapter for third-party submissions. That scope requires
a short-lived, revocable, budget-limited credential or a broker that keeps the
credential outside the agent process. The offline runner remains the default
for untrusted executable fixtures.

## Boundary invariants

- Never mount a canonical repository, host home, Codex home, or Docker socket
  writable into an agent container.
- Never use `--privileged`, host networking, broad environment forwarding, an
  unrestricted bridge network, or agent-side external DNS in hosted runs.
- Treat task text, repository content, model output, logs, issues, and review
  submissions as untrusted data, not authority.
- Use a fresh empty private output directory for each run and inspect exported
  results before opening or executing them.
- Keep credentials and raw hosted-run telemetry outside Git and published
  release artifacts.

The full runtime boundary and residual risks are documented in
[`docs/runner-isolation.md`](docs/runner-isolation.md).

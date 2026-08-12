# Container runner isolation

State: offline adapter and controlled-egress Codex adapter implemented and
locally calibrated for maintainer-controlled fixtures. Untrusted third-party
skills and tasks remain blocked by the reusable-credential boundary.

## Decision

Executable task fixtures run in disposable Docker containers by default. Docker
is an adapter behind the evidence contract, not the owner of experiment meaning
or a guarantee that arbitrary code is safe.

The canonical repository is never mounted writable. A run receives:

- one task fixture mounted read-only at `/fixture`;
- a private tmpfs copy at `/workspace/repo`;
- a disposable host staging directory mounted at `/output`, followed by a
  symlink- and special-file-rejecting copy into the requested empty output;
- either no network or one internal-only Docker network whose sole uplink is an
  allowlist proxy;
- a read-only container root filesystem;
- no Linux capabilities and no-new-privileges;
- numeric non-root host UID/GID;
- CPU, memory, process, time, workspace, and temporary-storage limits;
- no Docker socket, host home, or broad configuration-directory mount.

The entrypoint copies the fixture into tmpfs, executes one argv command without
an implicit shell, and exports the resulting workspace into staging. After the
container stops, the host rejects symlinks, special entries, and reserved
metadata names before copying staged files into the requested output. It then
records stdout, stderr, exit state, duration, image ID, limits, fixture hash,
and intervention hash. Outputs remain untrusted evidence until evaluated.

For hosted Codex calibration, only one explicitly named `auth.json` file is
mounted read-only. The entrypoint copies it into an ephemeral home directory;
the home is not exported. An optional skill directory is separately mounted
read-only and copied into that same ephemeral home. The invocation record stores
only whether these inputs were injected, never their host path or contents.

The agent container has no public route. The host resolves the proxy's private
network address, injects that IP as the HTTP(S) proxy, and disables DNS inside
the agent container. The proxy is the only dual-homed container and accepts
CONNECT requests only for port 443 and the exact hosts `api.openai.com`,
`auth.openai.com`, and `chatgpt.com`. There are no wildcard domains. Proxy logs
contain host, port, decision, and time—not HTTP headers, paths, bodies, or
credential values.

Codex runs with its inner sandbox disabled because its Linux namespace sandbox
cannot initialize inside the restricted outer container. This does not grant
host access: the outer Docker boundary still has a read-only root filesystem,
zero Linux capabilities, no-new-privileges, bounded tmpfs, a read-only canonical
fixture, one writable private export, and controlled egress.

Docker's own security boundary and resource controls are documented in the
[Docker Engine security guide](https://docs.docker.com/engine/security/) and
[resource constraints guide](https://docs.docker.com/engine/containers/resource_constraints/).
The fixture uses a read-only [bind mount](https://docs.docker.com/engine/storage/bind-mounts/)
and the default runner uses Docker's [`none` network](https://docs.docker.com/engine/network/drivers/none/).

## Commands

```bash
uv run ael sandbox doctor
uv run ael sandbox build --context docker/runner
uv run ael sandbox build \
  --context docker/codex-runner \
  --tag kizz/ael-codex-runner:0.146.0
uv run ael sandbox build \
  --context docker/egress-proxy \
  --tag kizz/ael-egress-proxy:0.1.0-alpha.1

mkdir -p artifacts/private
smoke_output="$(mktemp -d artifacts/private/smoke-output.XXXXXX)"
uv run ael sandbox run \
  --fixture docker/runner/smoke-fixture \
  --output "$smoke_output" \
  -- python mutate.py

AEL_CODEX_AUTH_FILE=/path/to/explicit/codex/auth.json
codex_output="artifacts/private/codex-calibration-example"
uv run ael sandbox codex \
  --fixture studies/focused-change-verification/task-pack/adaptation-v1/tasks/local-unit/fixture \
  --output "$codex_output" \
  --auth-file "$AEL_CODEX_AUTH_FILE" \
  --trusted-input-only \
  --model gpt-5.6-sol \
  --reasoning-effort xhigh
```

Normal experiment tooling should likewise allocate a fresh output path rather
than reuse one.

## What Docker does not solve

- A writable bind mount still grants write access to that host path.
- The staging mount protects arbitrary host paths from post-run symlink writes;
  it does not make staged content trustworthy or impose a strict host-disk
  quota on every exported file.
- Mounting the Docker socket is effectively host control and is forbidden.
- Root or `--privileged` containers weaken the boundary and are forbidden.
- Unrestricted network plus a model credential permits exfiltration.
- An exact-host CONNECT allowlist limits destinations, but it cannot inspect
  encrypted traffic or prevent a malicious agent from sending a readable
  credential to an allowed provider hostname.
- A malicious kernel/container-runtime exploit remains possible.
- Docker isolation does not make evaluator, task, or causal claims valid.
- Docker Desktop on macOS adds a Linux VM boundary but does not make result
  artifacts trustworthy.

## Model-access gate

The trusted-fixture gate now has evidence for a pinned Codex CLI image,
controlled egress, explicit single-file credential injection, exact-value scans
of persisted output, private raw telemetry, sanitized public records, and exact
container/network cleanup. A deterministic network smoke proved that an
allowlisted OpenAI endpoint was reachable through the proxy while an unrelated
host, a direct public-IP connection, and agent-side DNS resolution were blocked.

This does **not** pass the untrusted-content gate. Codex and its generated shell
commands run under the same container identity and can read the reusable
credential. The output scanner detects exact credential values after execution;
it is a persistence check, not prevention and not inspection of encrypted
provider traffic. Therefore:

- current hosted runs are limited to maintainer-controlled fixtures and skills;
- third-party submissions must not receive this credential path;
- a dedicated revocable credential with a hard budget or a broker that keeps
  credential material outside the agent process is required before that scope
  expands;
- unrestricted bridge networking, a broad Codex-home mount, and Docker-socket
  access remain forbidden.

The first six trusted calibration cells and their limitations are recorded in
[the Codex calibration report](../reports/2026-08-12-focused-change-verification-codex-calibration.md).

## Reversal

The adapter may later be replaced by a microVM, sandbox service, Kubernetes job,
or provider-native isolated runtime. A replacement must preserve or strengthen
the no-canonical-write, least-authority, resource-bound, provenance, cleanup,
and export guarantees; Contract v0 does not change.

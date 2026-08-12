# Container runner smoke: canonical fixture stayed immutable

Date: 2026-08-12  
State: locally validated on one macOS/OrbStack host; not independently reproduced  
Runner image: `kizz/ael-runner:0.1.0-dev`  
Local image ID: `sha256:dc1a5504413b5a45d537e6d16932e9f1a6729f18b564fccfa0c790a470287534`  
Fixture tree SHA-256: `1b5ee2c53e868027956118cda55c74d034c07ec5004f9ae7eb5acfbdecea1f05`

## Question

Can the minimal Docker adapter mutate a disposable workspace and export the
result while leaving the mounted source fixture unchanged and enforcing the
declared offline process boundary?

## Observed result

The fixture command completed with exit code `0`. Inside the container it:

- changed the tmpfs workspace copy;
- created a new workspace file;
- observed a read-only `/fixture` mount;
- observed a read-only root filesystem;
- ran as a numeric non-root user;
- observed zero effective Linux capabilities;
- observed `NoNewPrivs: 1`;
- found no Docker socket;
- failed to reach an external HTTPS endpoint under `--network none`.

The host-side fixture tree hash was identical before and after execution. The
mutated workspace, stdout, stderr, container result, and host invocation record
were exported only to an ignored private output directory.

## Boundary

This proves one local offline-adapter smoke path, not resistance to container
escape, malicious kernel exploitation, hosted credential exfiltration, or
correctness of an agent experiment. This specific smoke did not exercise the
separately implemented controlled-egress Codex adapter, so no hosted task run is
claimed by this report.

The executable contract and remaining model-access gate are in
[Container runner isolation](../docs/runner-isolation.md).

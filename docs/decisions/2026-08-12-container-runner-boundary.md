# Decision: agent execution uses disposable container workspaces

Date: 2026-08-12  
Status: offline adapter implemented and locally validated  
Route: direct engineering decision; no named advisor consultation occurred

## Decision

Use Docker as the default execution adapter for untrusted task fixtures, while
keeping Docker-specific mechanics outside Contract v0. Never give an agent a
writable mount of the canonical repository. Copy one read-only fixture into a
tmpfs workspace, run as non-root with bounded resources and no network, and
export only to a fresh ignored output directory.

Hosted-model access is a separate gate. The existing host Codex authentication
must not be mounted implicitly, and unrestricted bridge networking must not be
enabled merely to make a model call work.

## Binding evidence

The local smoke run changed the disposable workspace while preserving the
fixture tree hash. It observed a read-only fixture and root filesystem, non-root
identity, zero effective capabilities, no-new-privileges, no Docker socket, and
blocked external network. The exact bounded result is in
[the container runner smoke report](../../reports/2026-08-12-container-runner-smoke.md).

Docker remains a defense layer, not a proof of safety. The host daemon/runtime,
kernel boundary, writable export directory, future egress, and evaluator
integrity remain separate risks.

## Strongest rejected alternative

Run Codex directly in a canonical checkout and rely only on prompt discipline or
the agent's ordinary workspace sandbox. That is simpler but gives a
misconfigured or escaped runner a much larger blast radius and makes fixture
immutability harder to demonstrate.

## Residual decision

Before a hosted-model run, select one explicit authentication path and validate
it adversarially. A dedicated API project key with a hard spend limit and a
credential-brokering egress adapter is preferred for automation. Copying the
maintainer's reusable ChatGPT/Codex session into the agent container is not the
default.

Reconsider the adapter if a microVM or provider-native runner gives stronger
isolation with less credential and network complexity while preserving the AEL
receipt contract.


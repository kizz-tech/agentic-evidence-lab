# Decision: hosted Codex calibration is trusted-content only

Date: 2026-08-12  
Status: accepted for maintainer-controlled calibration; rejected for untrusted submissions  
Route: direct, reversible runner decision; no advisor consultation claimed

## Decision

Use the owner's explicitly selected Codex ChatGPT session for the first AEL
calibration runs, but expose only its single auth file to a pinned ephemeral
runner. Keep the agent on an internal-only network and route model traffic
through an exact-host CONNECT proxy. Preserve raw traces privately and publish
only content-addressed sanitized records.

Run Codex with its inner sandbox disabled because nested namespace creation
fails in the restricted container. Treat the outer Docker boundary—not prompt
discipline or Codex's inner sandbox—as the enforcement layer.

## Authorization and scope

The project owner explicitly selected this existing Codex session because it is
the actual development stack under study and does not add marginal model cost.
That authorization covers maintainer-controlled fixtures and the frozen Kizz
skill used in this calibration. It does not authorize mounting the broader
Codex home, publishing credentials, or executing third-party content with the
same reusable session.

## Evidence

- deterministic egress smoke: allowed OpenAI endpoint reachable, unrelated
  hostname and direct public IP blocked;
- six stable Codex cells exported evaluable workspaces while preserving source
  fixture hashes;
- pinned local runner and proxy image IDs recorded in every run record;
- no exact credential value found in the retained runtime-v2 outputs;
- exact proxy/container/network cleanup observed after runs.

See [the bounded calibration report](../../reports/2026-08-12-focused-change-verification-codex-calibration.md).

## Residual risk and next gate

The Codex process and its generated shell commands share an identity and can
read the credential. A hostname allowlist cannot inspect encrypted traffic to
an allowed provider endpoint. Post-run scanning detects persistence but cannot
prevent in-run disclosure.

Before third-party tasks or skills, use a dedicated revocable credential with a
hard budget or a broker that keeps reusable credential material outside the
agent process, then run an adversarial exfiltration suite. Revisit the outer
Docker design if a microVM or provider-native job offers a materially stronger
boundary without weakening evidence capture.

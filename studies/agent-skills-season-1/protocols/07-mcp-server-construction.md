# 07 — MCP server construction

State: protocol draft; public treatment was injected but not explicitly read;
activation task redesign, full SDK matrix, and effectiveness remain unrun.

## Decision question

Does the exact pinned Anthropic `mcp-builder` skill improve construction of MCP
servers that are protocol-conformant, usable by agents, and robust to invalid
inputs relative to the same coding stack without it?

## Conditions and task design

- `B0`: same model, runtime, SDK documentation bundle, tools, and budget.
- `S1`: `B0` plus exact mcp-builder.
- A placebo is required only if the added design context changes available
  factual information rather than procedure alone.

Task strata cover tool discovery, input schemas, error semantics, pagination,
side-effect confirmation, and local mock-service integration. External APIs are
simulated; no production credentials or network dependencies enter holdouts.

## Measurements and decision

Primary: protocol-conformant task completion across an independent client
suite. Secondary: tool-call success by a frozen consumer agent, schema quality,
unsafe side effects, error handling, unnecessary complexity, tokens, and time.
Passing a toy JSON-RPC calibration does not prove MCP SDK or production-service
readiness.

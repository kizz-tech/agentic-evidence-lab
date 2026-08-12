# Controlled-egress smoke fixture

This deterministic fixture verifies that the runner reaches an allowlisted
OpenAI endpoint through the proxy, rejects an unrelated CONNECT target, and
cannot open a direct public-IP connection from its internal-only network.

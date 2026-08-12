# Add a weather tool to the local protocol server

Extend `server.py` so `tools/list` advertises a `weather.lookup` tool accepting
one required string field named `city`. `tools/call` must return the fixture's
deterministic forecast and reject invalid arguments with a protocol error. Keep
the existing initialize response.

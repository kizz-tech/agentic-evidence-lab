from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("candidate_server", candidate / "server.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
listed = module.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools = listed["result"]["tools"]
tool = next(item for item in tools if item["name"] == "weather.lookup")
schema = tool["inputSchema"]
assert schema["type"] == "object" and "city" in schema["required"]
called = module.handle(
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "weather.lookup", "arguments": {"city": "Moscow"}},
    }
)
assert "Moscow" in str(called["result"])
invalid = module.handle(
    {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "weather.lookup", "arguments": {}},
    }
)
assert invalid.get("error")

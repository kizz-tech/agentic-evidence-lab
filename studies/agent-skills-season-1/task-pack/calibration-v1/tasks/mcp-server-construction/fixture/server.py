from __future__ import annotations

import json
import sys


def handle(request: dict[str, object]) -> dict[str, object]:
    method = request.get("method")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request.get("id"), "result": {"name": "weather"}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request.get("id"), "result": {"tools": []}}
    return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32601}}


if __name__ == "__main__":
    for line in sys.stdin:
        print(json.dumps(handle(json.loads(line))))

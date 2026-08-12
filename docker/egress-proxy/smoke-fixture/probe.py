from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from pathlib import Path


def allowed_endpoint_reached() -> bool:
    try:
        urllib.request.urlopen("https://api.openai.com/v1/models", timeout=15)
    except urllib.error.HTTPError as exc:
        return exc.code in {401, 403}
    except OSError:
        return False
    return True


def unrelated_endpoint_blocked() -> bool:
    try:
        urllib.request.urlopen("https://example.com", timeout=10)
    except urllib.error.URLError as exc:
        return "403" in str(exc.reason) or "egress denied" in str(exc.reason)
    except OSError:
        return True
    return False


def direct_ip_blocked() -> bool:
    try:
        connection = socket.create_connection(("1.1.1.1", 443), timeout=3)
    except OSError:
        return True
    connection.close()
    return False


def agent_dns_blocked() -> bool:
    try:
        socket.getaddrinfo("example.com", 443)
    except OSError:
        return True
    return False


result = {
    "allowed_endpoint_reached": allowed_endpoint_reached(),
    "unrelated_endpoint_blocked": unrelated_endpoint_blocked(),
    "direct_ip_blocked": direct_ip_blocked(),
    "agent_dns_blocked": agent_dns_blocked(),
}
Path("egress-result.json").write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if all(result.values()) else 1)

import json
import os
from pathlib import Path
from urllib.request import urlopen

source = Path("input.txt")
source.write_text(source.read_text(encoding="utf-8") + "workspace mutation\n", encoding="utf-8")
Path("created.txt").write_text("created inside isolated workspace\n", encoding="utf-8")

checks = {
    "non_root": os.geteuid() != 0,
    "docker_socket_absent": not Path("/var/run/docker.sock").exists(),
}

try:
    Path("/fixture/input.txt").write_text("forbidden\n", encoding="utf-8")
except OSError:
    checks["fixture_read_only"] = True
else:
    checks["fixture_read_only"] = False

try:
    Path("/root-filesystem-probe").write_text("forbidden\n", encoding="utf-8")
except OSError:
    checks["root_filesystem_read_only"] = True
else:
    checks["root_filesystem_read_only"] = False

status = {
    key: value.strip()
    for key, value in (
        line.split(":", 1)
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines()
        if ":" in line
    )
}
checks["no_new_privileges"] = status.get("NoNewPrivs") == "1"
checks["capabilities_dropped"] = int(status.get("CapEff", "1"), 16) == 0

try:
    urlopen("https://example.com", timeout=2)
except Exception:
    Path("network.txt").write_text("blocked\n", encoding="utf-8")
    checks["network_blocked"] = True
else:
    checks["network_blocked"] = False

Path("isolation.json").write_text(
    json.dumps(checks, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
if not all(checks.values()):
    raise SystemExit(f"isolation check failed: {checks}")

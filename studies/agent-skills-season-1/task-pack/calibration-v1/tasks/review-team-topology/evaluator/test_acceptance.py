from __future__ import annotations

import json
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
report = json.loads((candidate / "findings.json").read_text(encoding="utf-8"))
findings = report["findings"]
assert 2 <= len(findings) <= 5
joined = " ".join(str(item).lower() for item in findings)
assert "sql" in joined and ("inject" in joined or "parameter" in joined)
assert "lock" in joined and ("release" in joined or "deadlock" in joined)
assert all(item.get("evidence") for item in findings)

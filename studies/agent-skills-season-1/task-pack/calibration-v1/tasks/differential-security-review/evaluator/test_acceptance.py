from __future__ import annotations

import json
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
report = json.loads((candidate / "findings.json").read_text(encoding="utf-8"))
findings = report["findings"]
assert 1 <= len(findings) <= 3
joined = " ".join(str(item).lower() for item in findings)
assert "timing" in joined or "constant-time" in joined or "compare_digest" in joined
assert any(item.get("severity", "").lower() in {"high", "critical"} for item in findings)
assert "expected == supplied" in joined or "return expected" in joined

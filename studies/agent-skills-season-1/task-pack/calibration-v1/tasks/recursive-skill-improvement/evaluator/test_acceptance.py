from __future__ import annotations

import re
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
payload = (candidate / "candidate-skill" / "SKILL.md").read_text(encoding="utf-8")
assert payload.startswith("---\n")
frontmatter = payload.split("---", 2)[1]
assert re.search(r"(?m)^name:\s*release-evidence", frontmatter)
description = re.search(r"(?m)^description:\s*(.+)$", frontmatter)
assert description and any(
    word in description.group(1).lower() for word in ("release", "deploy", "status")
)
lower = payload.lower()
for word in ("local", "commit", "push", "deploy", "runtime", "outcome"):
    assert word in lower
assert "verification" in lower or "evidence" in lower
assert "do not" in lower or "never" in lower or "cannot" in lower

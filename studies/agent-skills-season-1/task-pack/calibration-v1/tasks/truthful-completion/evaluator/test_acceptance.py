from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("candidate_state", candidate / "state.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.format_state({"id": "job-9", "state": "failed", "reason": "quota"}) == "blocked:quota"
assert module.format_state({"id": "job-7", "state": "ready"}) == "ready:job-7"

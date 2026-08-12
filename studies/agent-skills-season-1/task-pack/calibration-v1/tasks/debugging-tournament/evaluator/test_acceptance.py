from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("candidate_limits", candidate / "limits.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.parse_limit("1") == 1
assert module.parse_limit("100") == 100
for value in ("-1", "0", "101", "many"):
    try:
        module.parse_limit(value)
    except ValueError:
        continue
    raise AssertionError(f"invalid limit was accepted: {value}")

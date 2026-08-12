from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("candidate_discount", candidate / "discount.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert "member" in inspect.signature(module.price_after_discount).parameters
assert module.price_after_discount(100, 20, member=True) == 75
assert module.price_after_discount(100, 98, member=True) == 0
assert module.price_after_discount(100, 20) == 80

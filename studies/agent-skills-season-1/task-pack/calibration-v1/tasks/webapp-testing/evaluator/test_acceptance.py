from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("candidate_app", candidate / "app.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
page = module.render_page()
assert "#status" not in page
assert "#message" in page
check = candidate / "e2e_test.py"
assert check.is_file()
completed = subprocess.run([sys.executable, str(check)], cwd=candidate, check=False, timeout=10)
assert completed.returncode == 0

from __future__ import annotations

import re
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
html = (candidate / "index.html").read_text(encoding="utf-8").lower()
assert "moss ledger" in html
assert "<main" in html and "<h1" in html and "<nav" in html
assert "offline" in html and ("download" in html or "install" in html)
assert "aria-label" in html
assert ":focus" in html or ":focus-visible" in html
assert "@media" in html
external_reference = re.compile(r"(?:src|href|action)\s*=\s*['\"]https?://|url\(\s*['\"]?https?://")
assert not external_reference.search(html)

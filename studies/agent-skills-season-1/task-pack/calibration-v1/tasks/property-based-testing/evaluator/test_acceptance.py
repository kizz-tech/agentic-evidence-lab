from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

candidate = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("candidate_codec", candidate / "codec.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
alphabet = "abЖ🙂é"
randomizer = random.Random(104729)
values = [
    "",
    "é",
    "Жук",
    "🙂agent",
    *(
        "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(0, 30)))
        for _ in range(50)
    ),
]
for value in values:
    assert module.decode(module.encode(value)) == value
try:
    module.encode("a" * 256)
except (ValueError, OverflowError):
    pass
else:
    raise AssertionError("oversized payload must be rejected")

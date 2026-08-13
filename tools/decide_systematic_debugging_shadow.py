from __future__ import annotations

import argparse
import json
from pathlib import Path

from ael.systematic_debugging_shadow import decide_effect


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    decision = decide_effect(args.freeze, args.observations)
    output = args.output.absolute()
    if output.exists():
        raise SystemExit(f"effect decision output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"effect decision: {decision['effect_outcome']} eligible={decision['eligible_strata']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

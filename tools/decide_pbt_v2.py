from __future__ import annotations

import argparse
import json
from pathlib import Path

from ael.pbt_pilot import decide_pbt_stage, pbt_confirmation_unlocked


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    decide = subparsers.add_parser("decide")
    decide.add_argument("--bundle", required=True, type=Path)
    decide.add_argument("--observations", required=True, type=Path)
    decide.add_argument(
        "--stage", required=True, choices=["continuation", "selection", "confirmation"]
    )
    decide.add_argument("--output", required=True, type=Path)
    unlock = subparsers.add_parser("unlock-check")
    unlock.add_argument("--bundle", required=True, type=Path)
    unlock.add_argument("--selection", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "unlock-check":
        if not pbt_confirmation_unlocked(args.bundle, args.selection):
            raise SystemExit("confirmation remains locked")
        print("confirmation unlock check passed")
        return 0
    decision = decide_pbt_stage(args.bundle, args.observations, args.stage)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PBT decision: stage={args.stage} outcome={decision['outcome']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

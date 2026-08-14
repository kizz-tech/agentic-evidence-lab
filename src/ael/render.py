from __future__ import annotations

from typing import Any


def render_receipt(receipt: dict[str, Any]) -> str:
    decision = receipt["decision"]
    independence = receipt["independence"]
    lines = [
        f"# Evidence receipt: {receipt['receipt_id']}",
        "",
        f"- Study: `{receipt['study_ref']['study_id']}`",
        f"- Decision: **{decision['disposition']}**",
        f"- Receipt evidence state: `{receipt['evidence_level']}`",
        f"- Independence: `{independence['label']}`",
        f"- Reproducibility: `{receipt['reproducibility']}`",
        f"- Publication state: `{receipt['publication_state']}`",
        "",
        "## Decision",
        "",
        decision["summary"],
        "",
        "### Scope",
        "",
        *[f"- {item}" for item in decision["scope"]],
        "",
        "## Evaluated claims",
        "",
    ]
    for claim in receipt["evaluated_claims"]:
        lines.extend(
            [
                f"### {claim['claim_id']} — {claim['status']}",
                "",
                claim["statement"],
                "",
                f"Claim class: `{claim['claim_level']}`",
                "",
                "Scope:",
                *[f"- {item}" for item in claim["scope"]],
                "",
                f"Falsifier: {claim['falsifier']}",
                "",
            ]
        )
    lines.extend(["## Unsupported inferences", ""])
    lines.extend(f"- {item}" for item in receipt["unsupported_inferences"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in receipt["limitations"])
    lines.extend(["", "## Independence and role overlap", ""])
    if independence["role_overlaps"]:
        lines.extend(f"- {item}" for item in independence["role_overlaps"])
    else:
        lines.append("- No declared role overlap.")
    lines.extend(["", "## Invalidation triggers", ""])
    lines.extend(f"- {item}" for item in receipt["invalidation_triggers"])
    lines.extend(["", "## State", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in receipt["state"].items())
    lines.append("")
    return "\n".join(lines)

"""Pure deterministic renderers for already-admitted public result values."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.result_constants import (
    GENERATOR_NAME,
    GENERATOR_VERSION,
    PUBLIC_STATUS_LABELS,
    PUBLICATION_PROJECTION_POLICY,
)


def json_bytes(value: Any) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    )


def _markdown_link(label: str, path: str, from_dir: str) -> str:
    target = Path(os.path.relpath(path, from_dir)).as_posix()
    return f"[{label}]({target})"


def _render_claim(claim: Mapping[str, Any]) -> list[str]:
    lines = [
        f"### {claim['claim_id']} — {claim['status']}",
        "",
        str(claim["statement"]),
        "",
        f"Claim class: `{claim['claim_level']}`",
        "",
        "Scope:",
        *[f"- {item}" for item in claim["scope"]],
        "",
        "Evidence references:",
    ]
    for binding in claim["evidence_bindings"]:
        if binding["binding"] == "measurement":
            role_suffix = (
                "; task-pack roles: "
                + ", ".join(f"`{role}`" for role in binding["task_pack_roles"])
                if binding["task_pack_roles"]
                else ""
            )
            lines.append(
                f"- `{binding['reference']}` — Measurement Set `{binding['measurement_kind']}`"
                f"{role_suffix}"
            )
        elif binding["binding"] == "public_sidecar":
            lines.append(
                f"- `{binding['reference']}` — public sidecar `{binding['uri']}` "
                f"(SHA-256 `{binding['sha256']}`)"
            )
        else:
            lines.append(
                f"- `{binding['reference']}` — opaque receipt reference; this projection "
                "does not independently resolve it"
            )
    lines.extend(["", f"Falsifier: {claim['falsifier']}", ""])
    return lines


def render_card(card: Mapping[str, Any]) -> str:
    card_directory = "docs/results"
    reproduction = card["reproduction"]
    lines = [
        f"# {card['title']}",
        "",
        f"- Card ID: `{card['card_id']}`",
        f"- Catalog state: **{card['catalog_state']}**",
        "",
        "## Decision",
        "",
        f"**{card['decision']['disposition']}** — {card['decision']['summary']}",
        "",
        "Scope:",
        *[f"- {item}" for item in card["decision"]["scope"]],
        "",
        f"Reversal trigger: {card['decision']['reversal_trigger']}",
        "",
    ]
    if "report" in card:
        lines.insert(
            4,
            f"- Narrative report: {_markdown_link('open', card['report']['uri'], card_directory)}",
        )
    lines.extend(["## Decision-governing claims", ""])
    for claim in card["claims"]:
        if not claim["decision_governing"]:
            continue
        lines.extend(_render_claim(claim))
    additional_claims = [claim for claim in card["claims"] if not claim["decision_governing"]]
    if additional_claims:
        lines.extend(
            [
                "## Additional selected claims",
                "",
                "These claims disclose supporting workflow or artifact facts; they do not "
                "govern the displayed disposition.",
                "",
            ]
        )
        for claim in additional_claims:
            lines.extend(_render_claim(claim))
    study = card["study"]
    lines.extend(
        [
            "## What was tested",
            "",
            study["decision_question"],
            "",
            f"Comparison mode: `{study['comparison_mode']}`. Study state: `{study['status']}`.",
            "",
            f"Primary estimand: **{study['primary_estimand']['name']}** — {study['primary_estimand']['description']}",
            "",
            "Conditions:",
            *[
                f"- `{condition['condition_id']}` — {condition['label']} "
                f"(`{condition['role']}`, `{condition['intervention_class']}`)"
                for condition in study["conditions"]
            ],
            "",
            "Task strata:",
            *[
                f"- `{task_pack['task_pack_id']}` (`{task_pack['role']}`): "
                + ", ".join(task_pack["strata"])
                for task_pack in study["task_packs"]
            ],
            "",
            "Decision owner(s): "
            + (", ".join(f"`{owner}`" for owner in study["decision_owners"]) or "not declared"),
            "",
            "## Observed runs, measurements, and cost",
            "",
            f"Runs: `{card['runs']['count']}`; by status: "
            + ", ".join(
                f"`{status}={count}`" for status, count in card["runs"]["by_status"].items()
            )
            + ".",
            "",
            f"Measurements: `{card['measurements']['count']}`; by kind: "
            + ", ".join(
                f"`{kind}={count}`" for kind, count in card["measurements"]["by_kind"].items()
            )
            + ".",
            "",
            "### Repeat and uncertainty evidence",
            "",
            f"- Repeat coverage: `{card['runs']['repeat_evidence']['status']}` across "
            f"`{card['runs']['repeat_evidence']['retained_task_condition_cells']}` retained "
            "task-condition cells.",
            "- Valid repeats per cell: "
            f"minimum `{card['runs']['repeat_evidence']['minimum_valid_repeats_per_cell']}`, "
            f"maximum `{card['runs']['repeat_evidence']['maximum_valid_repeats_per_cell']}`.",
            f"- Measurement intervals: `{card['measurements']['uncertainty']['status']}` "
            f"on `{card['measurements']['uncertainty']['measurement_count']}` measurements.",
            "",
            "These are facts about retained observations. The projection cannot infer a "
            "completely absent planned cell from Run Records alone. They are not a reliability "
            "grade, and planned repeat or perturbation coverage cannot substitute for observed data.",
            "",
        ]
    )
    if card["measurements"]["selected_summaries"]:
        lines.extend(["Selected descriptive totals (not stable effects):", ""])
        for summary in card["measurements"]["selected_summaries"]:
            if "total" in summary:
                value = f"total `{summary['total']:g} {summary['unit']}`"
            elif "true" in summary:
                value = f"true `{summary['true']}/{summary['observations']}`"
            else:
                value = str(summary["aggregation"])
            lines.append(
                f"- `{summary['metric']}` / `{summary['condition_id']}`: {value} "
                f"(`{summary['category']}`)"
            )
        lines.append("")
    lines.extend(["## Study design preflight", ""])
    lines.append(f"Status: `{card['quality']['status']}`; scope: `{card['quality']['scope']}`.")
    if "as_of" in card["quality"]:
        lines.append(f"Assessment as of: `{card['quality']['as_of']}`.")
    lines.append("")
    for key, value in card["quality"]["quality_axes"].items():
        label = "planned_reliability_coverage" if key == "reliability_coverage" else key
        lines.append(f"- `{label}`: `{value}`")
    if card["quality"]["issues"]:
        lines.extend(["", "Preflight findings:"])
        for issue in card["quality"]["issues"]:
            lines.append(
                f"- `{issue['severity']} {issue['code']}` `{issue['location']}` — {issue['message']}"
            )
    lines.extend(["", card["quality"]["boundary"], ""])
    lines.extend(["## Decision lifecycle", ""])
    for key in ("admission", "action", "outcome_follow_up", "freshness"):
        lines.append(f"- {key}: `{card['history'][key]}`")
    if "lifecycle" in card:
        lines.extend(["", "Declared lifecycle:"])
        for key, reference in card["lifecycle"]["refs"].items():
            lines.append(f"- `{key}`: `{reference['uri']}` (SHA-256 `{reference['sha256']}`)")
        lines.extend(
            [
                f"- adoption disposition: `{card['lifecycle']['adoption_disposition']}`",
                f"- action kind: `{card['lifecycle']['action_kind']}`",
                f"- follow-up due: `{card['lifecycle']['follow_up_due_at']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Replication and independence",
            "",
            f"- Public graph verification: `{reproduction['public_graph_verification']['status']}`",
            f"- Maintainer rerun: `{reproduction['study_rerun']['status']}`",
            f"- Independent replication: `{reproduction['independent_replication']['status']}`",
            f"- Evaluation ownership: `{card['independence']['label']}`",
            "",
            card["independence"]["disclosure"],
            "",
            "Maintainer rerun boundary:",
            "",
            reproduction["study_rerun"]["boundary"],
            "",
            "## Technical evidence",
            "",
            f"- Receipt: {_markdown_link('machine-readable evidence', card['receipt']['uri'], card_directory)}",
            f"- Receipt SHA-256: `{card['receipt']['sha256']}`",
            f"- Receipt evidence state: `{card['evidence_level']}`",
            f"- Receipt Contract v0 reproducibility field: `{card['receipt_reproducibility']}`",
            "",
            "The receipt evidence state and reproducibility field are retained Contract v0 "
            "compatibility metadata. Neither is a score, a public task-rerun claim, or proof "
            "of independent replication.",
            "",
            "### Verification boundary",
            "",
            f"Kind: `{card['verification']['kind']}`",
            "",
            card["verification"]["boundary"],
            "",
            "Command (presentation only; not executed by this generator):",
            "",
            "```sh",
            *[str(item) for item in card["verification"]["command"]],
            "```",
            "",
        ]
    )
    if "audit" in card["verification"]:
        audit = card["verification"]["audit"]
        lines.extend(
            [
                f"Audit status: `{audit['status']}`.",
                f"Contract documents checked: `{audit['evidence']['contract_documents']}`; "
                f"run records: `{audit['evidence']['run_records']}`.",
                "",
            ]
        )
    lines.extend(["", "## Materials", ""])
    for material in card["materials"]:
        lines.append(f"- **{material['label']}** — `{material['availability']}`")
        if material["availability"] == "public":
            lines.append(
                f"  - Ref: `{material['ref']['uri']}` (SHA-256 `{material['ref']['sha256']}`)"
            )
        else:
            lines.append(f"  - Reason: {material['reason']}")
            lines.append(f"  - Reproduction impact: {material['reproduction_impact']}")
    lines.extend(["", "## Unsupported inferences", ""])
    lines.extend(f"- {item}" for item in card["unsupported_inferences"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in card["limitations"])
    lines.extend(["", "## Invalidation triggers", ""])
    lines.extend(f"- {item}" for item in card["invalidation_triggers"])
    lines.extend(["", "## Source hashes", ""])
    lines.extend(f"- `{path}` — `{digest}`" for path, digest in card["source_hashes"].items())
    lines.extend(
        [
            "",
            f"Generated by `{GENERATOR_NAME}` `{GENERATOR_VERSION}` under `{PUBLICATION_PROJECTION_POLICY}`.",
            "",
        ]
    )
    return "\n".join(lines)


def render_results(results: list[Mapping[str, Any]], as_of: str) -> str:
    lines = [
        "# Results Index",
        "",
        f"Generated as of `{as_of}` from the explicit result-catalog profile.",
        "",
        "This claim-first index shows bounded decisions before technical receipt metadata. "
        "`listed` means the result is selected for this catalog; it is not proof of a Git "
        "tag or GitHub release. Decision-governing claim states, study-design evidence, observed repeat "
        "coverage, replication, outcome, and freshness are independent and must not be "
        "collapsed into a score.",
        "",
        "| Study | Catalog | Decision | Decision-governing claims | Design preflight | Repeat evidence | Independent replication | Outcome follow-up | Freshness |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for card in results:
        decision = card["decision"]["disposition"]
        reproduction = card["reproduction"]
        claim_counts: dict[str, int] = {}
        for claim in card["claims"]:
            if not claim["decision_governing"]:
                continue
            status = str(claim["status"])
            claim_counts[status] = claim_counts.get(status, 0) + 1
        status_order = ("supported", "contradicted", "bounded", "unresolved")
        claims = " · ".join(
            f"{claim_counts[status]} {status}" for status in status_order if status in claim_counts
        )
        lines.append(
            f"| [{card['title']}](docs/results/{card['card_id']}.md) | "
            f"`{card['catalog_state']}` | **{decision}** | {claims} | "
            f"{PUBLIC_STATUS_LABELS.get(card['quality']['status'], card['quality']['status'])} | "
            f"{PUBLIC_STATUS_LABELS.get(card['runs']['repeat_evidence']['status'], card['runs']['repeat_evidence']['status'])} | "
            f"{PUBLIC_STATUS_LABELS.get(reproduction['independent_replication']['status'], reproduction['independent_replication']['status'])} | "
            f"{PUBLIC_STATUS_LABELS.get(card['history']['outcome_follow_up'], card['history']['outcome_follow_up'])} | "
            f"{PUBLIC_STATUS_LABELS.get(card['history']['freshness'], card['history']['freshness'])} |"
        )
    lines.extend(
        [
            "",
            f"Generated by `{GENERATOR_NAME}` `{GENERATOR_VERSION}` under `{PUBLICATION_PROJECTION_POLICY}`.",
            "",
        ]
    )
    return "\n".join(lines)

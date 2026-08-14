"""Stable identifiers and presentation labels for the public result surface."""

from __future__ import annotations

from types import MappingProxyType

from ael import __version__

PUBLIC_RESULTS_SCHEMA_VERSION = "ael.public-results/0.5"
PUBLICATION_PROJECTION_POLICY = "ael.publication-projection/0.5"
GENERATOR_NAME = "agentic-evidence-lab"
GENERATOR_VERSION = __version__

PUBLIC_STATUS_LABELS = MappingProxyType(
    {
        "not_assessed_historical": "historical · not assessed",
        "retained_cell_without_valid_observation": "retained cell without a valid run",
        "single_valid_observation_per_retained_cell": "1 valid run / retained cell",
        "repeated_valid_observations_per_retained_cell": "2+ valid runs / retained cell",
        "mixed_valid_repeat_coverage": "mixed valid repeats",
        "none_linked": "none linked",
        "not_declared_historical": "not declared (historical)",
        "scheduled:not_due": "scheduled · not due",
        "within_declared_window": "within declared window",
        "unassessed": "unassessed",
    }
)

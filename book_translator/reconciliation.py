"""Reconciliation utilities for multi-backend outputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(slots=True)
class ReconciliationResult:
    """Consensus output and disagreement metadata."""

    text: str
    disagreement_count: int


def reconcile_text_variants(variants: dict[str, str], marker_prefix: str = "[DIFF]") -> ReconciliationResult:
    """Create a majority-vote reconciliation across line-aligned backend outputs."""
    if not variants:
        raise ValueError("cannot reconcile empty variant mapping")

    normalized = {name: value.strip("\n") for name, value in variants.items()}
    split_variants = {name: value.splitlines() for name, value in normalized.items()}
    max_line_count = max(len(lines) for lines in split_variants.values())

    reconciled_lines: list[str] = []
    disagreement_count = 0

    for index in range(max_line_count):
        line_candidates: dict[str, str] = {}
        for backend_name, lines in split_variants.items():
            line_candidates[backend_name] = lines[index] if index < len(lines) else ""

        value_counts = Counter(line_candidates.values())
        winner, winner_count = value_counts.most_common(1)[0]
        if len(value_counts) > 1 and winner_count < len(line_candidates):
            disagreement_count += 1
            variant_summary = " | ".join(
                f"{name}={value!r}" for name, value in sorted(line_candidates.items())
            )
            reconciled_lines.append(f"{marker_prefix} line={index + 1} {variant_summary}")

        # Bias toward richer line when winner is empty and any non-empty candidate exists.
        selected_line = winner
        if not selected_line:
            non_empty_values = [value for value in line_candidates.values() if value]
            if non_empty_values:
                selected_line = max(non_empty_values, key=len)

        if selected_line:
            reconciled_lines.append(str(selected_line))

    return ReconciliationResult(text="\n".join(reconciled_lines).strip() + "\n", disagreement_count=disagreement_count)


def similarity_score(candidate: str, reference: str) -> float:
    """Compute a rough similarity score between candidate and reference text."""
    if not candidate and not reference:
        return 1.0
    if not candidate or not reference:
        return 0.0
    return SequenceMatcher(a=candidate, b=reference).ratio()

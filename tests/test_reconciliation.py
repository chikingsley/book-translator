"""Tests for reconciliation behavior."""

from book_translator.reconciliation import reconcile_text_variants, similarity_score


def test_reconcile_prefers_majority_lines() -> None:
    """Prefer majority line variants and count disagreements."""
    result = reconcile_text_variants(
        {
            "a": "line 1\nline 2\nline 3",
            "b": "line 1\nline 2\nline 3",
            "c": "line 1\nline two\nline 3",
        }
    )

    assert "line 2" in result.text
    assert result.disagreement_count == 1


def test_similarity_score_bounds() -> None:
    """Return expected boundary values for similarity scoring."""
    assert similarity_score("same", "same") == 1.0
    assert similarity_score("", "different") == 0.0


"""Evaluate retrieved evidence and preserve per-query traces."""

import re
from typing import Any


def _normalize_text(text: str) -> str:
    """Normalize text for evidence matching."""
    text = text.casefold()
    text = text.replace("|", "")
    return re.sub(r"\s+", " ", text).strip()


def _gold_pairs(question: dict[str, Any]) -> set[tuple[str, int]]:
    """Build accepted (source_id, page) pairs."""
    sources = question.get("gold_source_id", [])
    pages = question.get("gold_page", [])

    if isinstance(sources, str):
        sources = [sources]

    if isinstance(pages, int):
        pages = [pages]

    if len(sources) == 1 and len(pages) > 1:
        sources = sources * len(pages)

    if len(pages) == 1 and len(sources) > 1:
        pages = pages * len(sources)

    if len(sources) != len(pages):
        raise ValueError(
            f"Gold source/page mismatch in question {question.get('id')}"
        )

    return {
        (source, page)
        for source, page in zip(sources, pages)
    }


def evaluate_query(
    question: dict[str, Any],
    hits: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate source/page retrieval and complete evidence coverage."""

    gold_pairs = _gold_pairs(question)

    # Hit@1: top result must match an accepted gold source and page.
    hit_at_1 = False

    if hits:
        first = hits[0]
        hit_at_1 = (
            first["document_id"],
            first["page"],
        ) in gold_pairs

    # Only evidence from accepted gold source/page pairs counts.
    gold_hits = [
        hit
        for hit in hits[:3]
        if (hit["document_id"], hit["page"]) in gold_pairs
    ]

    retrieved_text = _normalize_text(
        " ".join(hit["text"] for hit in gold_hits)
    )

    evidence_quotes = question.get("evidence_quote", [])

    if isinstance(evidence_quotes, str):
        evidence_quotes = [evidence_quotes]

    matched_quotes = []
    missing_quotes = []

    for quote in evidence_quotes:
        normalized_quote = _normalize_text(quote)

        if normalized_quote and normalized_quote in retrieved_text:
            matched_quotes.append(quote)
        else:
            missing_quotes.append(quote)

    evidence_hit_at_3 = (
        len(evidence_quotes) > 0
        and len(missing_quotes) == 0
    )

    return {
        "question_id": question["id"],
        "split": question["split"],
        "question": question["question"],
        "hit_at_1": hit_at_1,
        "evidence_hit_at_3": evidence_hit_at_3,
        "evidence_quote_count": len(evidence_quotes),
        "matched_quotes": matched_quotes,
        "missing_quotes": missing_quotes,
        "gold_pairs": [
            {"document_id": source, "page": page}
            for source, page in sorted(gold_pairs)
        ],
        "hits": hits[:3],
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and split."""

    summary = {}

    strategies = sorted({
        trace["strategy"]
        for trace in traces
    })

    for strategy in strategies:
        summary[strategy] = {}

        for split in ("dev", "test"):
            group = [
                trace
                for trace in traces
                if trace["strategy"] == strategy
                and trace["split"] == split
            ]

            count = len(group)

            if count == 0:
                summary[strategy][split] = {
                    "question_count": 0,
                    "hit_at_1": None,
                    "evidence_hit_at_3": None,
                }
                continue

            summary[strategy][split] = {
                "question_count": count,
                "hit_at_1": sum(
                    trace["hit_at_1"] for trace in group
                ) / count,
                "evidence_hit_at_3": sum(
                    trace["evidence_hit_at_3"] for trace in group
                ) / count,
            }

    return summary

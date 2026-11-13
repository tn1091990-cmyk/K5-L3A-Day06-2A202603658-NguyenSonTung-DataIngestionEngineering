
from src.evaluation import evaluate_query, summarize


question = {
    "id": "TEST01",
    "split": "dev",
    "question": "How many cores and threads?",
    "gold_source_id": ["amd-ryzen-3-8300g"],
    "gold_page": 1,
    "evidence_quote": [
        "# of Cores: 4",
        "# of Threads: 8",
    ],
}

hits = [
    {
        "document_id": "amd-ryzen-3-8300g",
        "page": 1,
        "text": "CPU specifications. # of Cores: 4",
        "score": 0.95,
    },
    {
        "document_id": "amd-ryzen-3-8300g",
        "page": 1,
        "text": "# of Threads: 8",
        "score": 0.90,
    },
]

result = evaluate_query(question, hits)

print("--- Evaluation result ---")
print(result)

assert result["hit_at_1"] is True
assert result["evidence_hit_at_3"] is True
assert len(result["matched_quotes"]) == 2
assert len(result["missing_quotes"]) == 0

# Test failure when one required quote is missing.
incomplete_hits = [hits[0]]

failed_result = evaluate_query(question, incomplete_hits)

assert failed_result["hit_at_1"] is True
assert failed_result["evidence_hit_at_3"] is False
assert len(failed_result["missing_quotes"]) == 1

# Test summary.
traces = [
    {"strategy": "A", **result},
    {"strategy": "A", **failed_result},
]

print("\n--- Summary ---")
print(summarize(traces))

print("\nAll evaluation tests passed!")

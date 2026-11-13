
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

with open(
    PROJECT_ROOT / "results/retrieval_traces.json",
    encoding="utf-8"
) as f:
    data = json.load(f)

traces = data["traces"]

for strategy in ["A", "B", "C"]:
    trace = next(
        item for item in traces
        if item["question_id"] == "Q01"
        and item["strategy"] == strategy
    )

    print(f"\nStrategy {strategy}")
    print("=" * 70)

    for rank, hit in enumerate(trace["hits"], start=1):
        print(
            f"Rank {rank}: {hit['chunk_id']} "
            f"(score={hit['score']:.4f})"
        )

        # Show whether this chunk contains the expected evidence
        text = hit["text"]
        has_cores = "# of Cores" in text
        has_threads = "# of Threads" in text

        print(
            f"  Contains core evidence: {has_cores}"
        )
        print(
            f"  Contains thread evidence: {has_threads}"
        )

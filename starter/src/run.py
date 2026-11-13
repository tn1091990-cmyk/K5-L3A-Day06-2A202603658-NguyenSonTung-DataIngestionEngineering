
"""Pipeline entry point for the Day 06 RAG benchmark."""

import os
import json

from pathlib import Path
from dotenv import load_dotenv
from src.evaluation import evaluate_query, summarize
from src.ingestion import load_html_directory
from src.metadata_cpu import enrich_cpu_metadata
from src.chunking import fixed_size, by_paragraph

from src.embeddings import MyEmbedder
from src.store import PgVectorStore

# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")


def prepare_corpus():
    """Load documents, enrich metadata, and build A/B/C chunks."""

    # 1. Load HTML documents.
    pages = load_html_directory(str(DATA_DIR))

    if len(pages) < 30:
        raise ValueError(
            f"Expected at least 30 documents, found {len(pages)}."
        )

    print(f"Loaded documents: {len(pages)}")

    # 2. Enrich CPU metadata.
    enriched_pages = [
        enrich_cpu_metadata(page)
        for page in pages
    ]

    print(f"Enriched documents: {len(enriched_pages)}")

    # 3. Read chunking configuration.
    fixed_size_value = int(os.getenv("FIXED_CHUNK_SIZE", "1000"))
    fixed_overlap = int(os.getenv("FIXED_CHUNK_OVERLAP", "150"))
    paragraph_max_size = int(os.getenv("PARAGRAPH_MAX_SIZE", "1000"))

    # 4. Build Strategy A: fixed-size chunks.
    chunks_a = []

    for page in enriched_pages:
        chunks_a.extend(
            fixed_size(
                page,
                size=fixed_size_value,
                overlap=fixed_overlap,
            )
        )

    # 5. Build Strategy B: paragraph-based chunks.
    chunks_b = []

    for page in enriched_pages:
        chunks_b.extend(
            by_paragraph(
                page,
                max_size=paragraph_max_size,
            )
        )

    # 6. Strategy C reuses Strategy B's chunks.
    chunks_c = chunks_b

    print("\n--- Chunk preparation summary ---")
    print(f"Strategy A chunks: {len(chunks_a)}")
    print(f"Strategy B chunks: {len(chunks_b)}")
    print(f"Strategy C chunks: {len(chunks_c)}")

    return enriched_pages, chunks_a, chunks_b, chunks_c

def embed_and_store(chunks_a, chunks_b, chunks_c):
    """Generate embeddings and store all three strategies."""

    # 1. Load configuration.
    database_url = os.getenv("DATABASE_URL")
    model_name = os.getenv("EMBEDDING_MODEL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env")

    if not model_name:
        raise ValueError("EMBEDDING_MODEL is missing from .env")

    # 2. Initialize embedding provider.
    print("\nInitializing embedding model...")
    embedder = MyEmbedder(model_name=model_name)

    print(f"Model: {embedder.model_name}")
    print(f"Dimensions: {embedder.dimensions}")

    # 3. Generate embeddings for Strategy A.
    print("\nEmbedding Strategy A...")
    vectors_a = embedder.embed_documents(
        [chunk.text for chunk in chunks_a]
    )
    print(f"Generated {len(vectors_a)} vectors for A.")

    # 4. Generate embeddings for Strategy B.
    print("\nEmbedding Strategy B...")
    vectors_b = embedder.embed_documents(
        [chunk.text for chunk in chunks_b]
    )
    print(f"Generated {len(vectors_b)} vectors for B.")

    # 5. Strategy C reuses B's embeddings.
    vectors_c = vectors_b

    assert chunks_c is chunks_b
    assert vectors_c is vectors_b

    print("Strategy C reuses Strategy B's chunks and vectors.")

    # 6. Initialize PostgreSQL storage.
    print("\nInitializing PostgreSQL storage...")
    store = PgVectorStore(
        database_url=database_url,
        dimensions=embedder.dimensions,
    )

    store.create_schema()
    print("Database schema ready.")

    # 7. Store each strategy separately.
    print("\nStoring Strategy A...")
    store.upsert("A", chunks_a, vectors_a)

    print("Storing Strategy B...")
    store.upsert("B", chunks_b, vectors_b)

    print("Storing Strategy C...")
    store.upsert("C", chunks_c, vectors_c)

    print("\n--- Storage summary ---")
    print(f"Strategy A: {len(chunks_a)} chunks")
    print(f"Strategy B: {len(chunks_b)} chunks")
    print(f"Strategy C: {len(chunks_c)} chunks")

    return store, embedder

def load_benchmark_questions():
    """Load benchmark questions from JSON."""

    configured_path = os.getenv("BENCHMARK_PATH")

    if configured_path:
        benchmark_path = Path(configured_path)

        if not benchmark_path.is_absolute():
            benchmark_path = PROJECT_ROOT / benchmark_path

        candidates = [benchmark_path]
    else:
        candidates = [
            PROJECT_ROOT / "benchmark_questions_vi.json",
            PROJECT_ROOT.parent / "benchmark_questions_vi.json",
            DATA_DIR / "benchmark_questions_vi.json",
        ]

    benchmark_path = next(
        (path for path in candidates if path.is_file()),
        None,
    )

    if benchmark_path is None:
        raise FileNotFoundError(
            "Cannot find benchmark_questions_vi.json. "
            "Place it in the starter directory or set BENCHMARK_PATH."
        )

    with benchmark_path.open("r", encoding="utf-8") as file:
        benchmark = json.load(file)

    questions = benchmark.get("questions")

    if not isinstance(questions, list) or len(questions) < 20:
        raise ValueError(
            "Benchmark must contain at least 20 questions "
            "inside the 'questions' list."
        )

    for question in questions:
        required = [
            "id",
            "split",
            "question",
            "gold_source_id",
            "gold_page",
            "evidence_quote",
        ]

        missing = [
            field for field in required
            if field not in question
        ]

        if missing:
            raise ValueError(
                f"Question {question.get('id', 'UNKNOWN')} "
                f"is missing fields: {missing}"
            )

        if question["split"] not in ("dev", "test"):
            raise ValueError(
                f"Invalid split in question {question['id']}"
            )

    print(f"Benchmark loaded: {benchmark_path}")
    print(f"Questions: {len(questions)}")

    return questions


def run_benchmark_retrieval(store, embedder, questions):
    """Retrieve and evaluate the same questions across A, B and C."""

    strategies = ["A", "B", "C"]
    traces = []

    total = len(questions)

    for index, question in enumerate(questions, start=1):
        question_id = question["id"]

        print(
            f"\n[{index}/{total}] "
            f"Processing {question_id}..."
        )

        # Generate the query embedding only once.
        query_vector = embedder.embed_query(
            question["question"]
        )

        for strategy in strategies:

            # Only Strategy C uses benchmark metadata filters.
            filters = None

            if strategy == "C":
                filters = question.get("filter")

            hits = store.search(
                strategy=strategy,
                query_vector=query_vector,
                top_k=3,
                filters=filters,
            )

            evaluation = evaluate_query(
                question=question,
                hits=hits,
            )

            trace = {
                "strategy": strategy,
                "filter": filters,
                **evaluation,
            }

            traces.append(trace)

            print(
                f"  {strategy}: "
                f"Hit@1={evaluation['hit_at_1']}, "
                f"Evidence Hit@3="
                f"{evaluation['evidence_hit_at_3']}, "
                f"Retrieved={len(hits)}"
            )

    return traces

def save_retrieval_results(traces, embedder):
    """Save retrieval traces and aggregated metrics."""

    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize(traces)

    trace_output = {
        "embedding_model": embedder.model_name,
        "embedding_dimensions": embedder.dimensions,
        "top_k": 3,
        "strategies": ["A", "B", "C"],
        "traces": traces,
    }

    trace_path = results_dir / "retrieval_traces.json"

    with trace_path.open("w", encoding="utf-8") as file:
        json.dump(
            trace_output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    summary_path = results_dir / "retrieval_summary.json"

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(
            summary,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\n--- Retrieval Summary ---")

    for strategy, splits in summary.items():
        print(f"\nStrategy {strategy}:")

        for split, metrics in splits.items():
            print(f"  {split}: {metrics}")

    print("\nSaved results:")
    print(f"  {trace_path}")
    print(f"  {summary_path}")

    return summary


def main() -> None:
    """Run benchmark retrieval against previously stored strategies."""

    # Load .env.
    load_dotenv(PROJECT_ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")
    model_name = os.getenv("EMBEDDING_MODEL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing.")

    if not model_name:
        raise ValueError("EMBEDDING_MODEL is missing.")

    # Load benchmark.
    questions = load_benchmark_questions()

    # Initialize embedding provider.
    print("\nInitializing embedding model...")
    embedder = MyEmbedder(model_name=model_name)

    print(f"Model: {embedder.model_name}")
    print(f"Dimensions: {embedder.dimensions}")

    # Connect to existing vector storage.
    store = PgVectorStore(
        database_url=database_url,
        dimensions=embedder.dimensions,
    )

    # Retrieve and evaluate.
    print("\nStarting benchmark retrieval...")

    traces = run_benchmark_retrieval(
        store=store,
        embedder=embedder,
        questions=questions,
    )

    # Save traces and summary.
    save_retrieval_results(traces, embedder)

    print("\nStage 3 completed successfully.")


if __name__ == "__main__":
    main()

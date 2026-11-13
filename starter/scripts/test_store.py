
import os

import psycopg
from dotenv import load_dotenv

from src.embeddings import MyEmbedder
from src.models import Chunk
from src.store import PgVectorStore


load_dotenv()

database_url = os.getenv("DATABASE_URL")
model_name = os.getenv("EMBEDDING_MODEL")

if not database_url:
    raise ValueError("DATABASE_URL is missing from .env")

if not model_name:
    raise ValueError("EMBEDDING_MODEL is missing from .env")


# Initialize embedding provider and database.
embedder = MyEmbedder(model_name=model_name)

store = PgVectorStore(
    database_url=database_url,
    dimensions=embedder.dimensions,
)

print("Creating database schema...")
store.create_schema()
print("Schema ready!")


# Use an isolated test document.
strategy = "TEST"
document_id = "__store_smoke_test__"
test_marker = "store-smoke-test"

texts = [
    "AMD Ryzen 7 9700X has 8 cores and 16 threads.",
    "AMD Ryzen 7 9700X has a maximum boost clock of 5.5 GHz.",
]

chunks = [
    Chunk(
        chunk_id="store-smoke-001",
        document_id=document_id,
        source="manual-test",
        page=1,
        text=texts[0],
        metadata={
            "series": "Ryzen 7",
            "architecture": "Zen 5",
            "test_run": test_marker,
        },
    ),
    Chunk(
        chunk_id="store-smoke-002",
        document_id=document_id,
        source="manual-test",
        page=1,
        text=texts[1],
        metadata={
            "series": "Ryzen 7",
            "architecture": "Zen 5",
            "test_run": test_marker,
        },
    ),
]


try:
    # 1. Generate embeddings and insert chunks.
    print("\nTesting insertion...")

    vectors = embedder.embed_documents(texts)

    store.upsert(strategy, chunks, vectors)

    print("Inserted 2 chunks.")

    # 2. Test vector similarity search.
    print("\nTesting vector search...")

    query = "How many cores does Ryzen 7 9700X have?"
    query_vector = embedder.embed_query(query)

    hits = store.search(
        strategy=strategy,
        query_vector=query_vector,
        top_k=10,
    )

    test_hits = [
        hit for hit in hits
        if hit["document_id"] == document_id
    ]

    assert len(test_hits) == 2
    assert all("score" in hit for hit in test_hits)

    print("Vector search returned the test chunks.")

    # 3. Test metadata filtering.
    print("\nTesting metadata filtering...")

    filtered_hits = store.search(
        strategy=strategy,
        query_vector=query_vector,
        top_k=10,
        filters={
            "test_run": test_marker,
            "series": "Ryzen 7",
        },
    )

    assert len(filtered_hits) == 2
    assert all(
        hit["metadata"]["test_run"] == test_marker
        for hit in filtered_hits
    )

    print("Metadata filtering passed.")

    # 4. Test replacement with fewer chunks.
    print("\nTesting document replacement...")

    replacement_text = "AMD Ryzen 7 9700X has 8 cores."

    replacement_chunk = Chunk(
        chunk_id="store-smoke-001",
        document_id=document_id,
        source="manual-test",
        page=1,
        text=replacement_text,
        metadata={
            "series": "Ryzen 7",
            "architecture": "Zen 5",
            "test_run": test_marker,
        },
    )

    replacement_vector = embedder.embed_documents(
        [replacement_text]
    )

    store.upsert(
        strategy,
        [replacement_chunk],
        replacement_vector,
    )

    replacement_hits = store.search(
        strategy=strategy,
        query_vector=query_vector,
        top_k=10,
        filters={"test_run": test_marker},
    )

    assert len(replacement_hits) == 1
    assert replacement_hits[0]["chunk_id"] == "store-smoke-001"

    print("Replacement passed: obsolete chunk removed.")

    print("\nAll storage tests passed!")

finally:
    # Remove only this test's records.
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM rag_chunks
                WHERE strategy = %s
                  AND document_id = %s
                """,
                (strategy, document_id),
            )

    print("Test records cleaned up.")

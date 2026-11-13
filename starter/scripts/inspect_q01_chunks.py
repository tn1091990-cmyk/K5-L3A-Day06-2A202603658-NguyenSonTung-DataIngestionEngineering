
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

database_url = os.getenv("DATABASE_URL")

query = """
    SELECT strategy, chunk_id, text
    FROM rag_chunks
    WHERE document_id = %s
      AND (
          text ILIKE '%%# of Cores%%'
          OR text ILIKE '%%# of Threads%%'
      )
    ORDER BY strategy, chunk_id;
"""

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                "amd-ryzen-3-8300g",
            ),
        )

        rows = cur.fetchall()

print("Chunks containing core/thread evidence:")
print("=" * 70)

for strategy, chunk_id, text in rows:
    print(f"\nStrategy: {strategy}")
    print(f"Chunk: {chunk_id}")
    print(text)
    print("-" * 70)

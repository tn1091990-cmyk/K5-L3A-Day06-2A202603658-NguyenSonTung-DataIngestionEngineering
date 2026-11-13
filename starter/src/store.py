"""TODO: store and search vectors using PostgreSQL + pgvector."""
import json
import math
import psycopg
from typing import Any
from .models import Chunk



class PgVectorStore:
    TABLE_NAME = "rag_chunks"
    def __init__(self, database_url: str, dimensions: int) -> None:
        """TODO: retain connection settings; validate model dimensions."""
        #raise NotImplementedError("TODO: initialize store")
        if not isinstance(dimensions, int) or isinstance(dimensions, bool) or dimensions <= 0:
            raise ValueError("dimensions must be a positive integer.")

        if not database_url:
            raise ValueError("database_url must not be empty.")

        self.database_url = database_url
        self.dimensions = dimensions

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        """Convert a vector into pgvector's textual representation."""
        return "[" + ",".join(str(float(value)) for value in vector) + "]"

    def _validate_vector(self, vector: list[float]) -> None:
        """Validate vector dimensions and numeric values."""
        if len(vector) != self.dimensions:
            raise ValueError(
                f"Expected {self.dimensions} dimensions, "
                f"received {len(vector)}."
            )

        for value in vector:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Embedding values must be numeric.")

            if not math.isfinite(value):
                raise ValueError("Embedding contains invalid values.")


    def create_schema(self) -> None:
        """TODO: create table with vector column and source/page/filter metadata."""
        #raise NotImplementedError("TODO: create_schema")
        query = f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                strategy TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                source TEXT NOT NULL,
                page INTEGER NOT NULL,
                text TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding VECTOR({self.dimensions}) NOT NULL,
                PRIMARY KEY (strategy, chunk_id)
            );
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS
                    idx_rag_chunks_strategy
                    ON rag_chunks (strategy);
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS
                    idx_rag_chunks_metadata
                    ON rag_chunks USING GIN (metadata);
                """)

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Replace all chunks for the supplied documents and strategy.

        Each call must contain the complete chunk set for every document
        represented in the input.
        """
        if not strategy:
            raise ValueError("strategy must not be empty.")

        if len(chunks) != len(vectors):
            raise ValueError(
                "Number of chunks must match number of vectors."
            )

        # An empty input cannot identify which existing documents
        # should be replaced, so it is treated as a no-op.
        if not chunks:
            return

        document_ids = set()
        seen_chunk_ids = set()
        rows = []

        for chunk, vector in zip(chunks, vectors):
            if not isinstance(chunk.metadata, dict):
                raise ValueError("Chunk metadata must be a dictionary.")

            if not chunk.document_id or not chunk.chunk_id:
                raise ValueError("Chunk IDs must not be empty.")

            if chunk.chunk_id in seen_chunk_ids:
                raise ValueError(
                    f"Duplicate chunk ID: {chunk.chunk_id}"
                )

            seen_chunk_ids.add(chunk.chunk_id)
            document_ids.add(chunk.document_id)

            self._validate_vector(vector)

            try:
                metadata_json = json.dumps(
                    chunk.metadata,
                    ensure_ascii=False,
                    allow_nan=False,
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid metadata for chunk {chunk.chunk_id}."
                ) from exc

            rows.append((
                strategy,
                chunk.chunk_id,
                chunk.document_id,
                chunk.source,
                chunk.page,
                chunk.text,
                metadata_json,
                self._vector_literal(vector),
            ))

        insert_query = f"""
            INSERT INTO {self.TABLE_NAME} (
                strategy,
                chunk_id,
                document_id,
                source,
                page,
                text,
                metadata,
                embedding
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s::jsonb,
                %s::vector
            )
            ON CONFLICT (strategy, chunk_id)
            DO UPDATE SET
                document_id = EXCLUDED.document_id,
                source = EXCLUDED.source,
                page = EXCLUDED.page,
                text = EXCLUDED.text,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding;
        """

        delete_query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE strategy = %s
              AND document_id = ANY(%s);
        """

        # Delete and insert are part of the same transaction.
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    delete_query,
                    (strategy, list(document_ids)),
                )

                cur.executemany(insert_query, rows)


    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search by cosine similarity with optional metadata filters."""
        if not strategy:
            raise ValueError("strategy must not be empty.")

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        self._validate_vector(query_vector)

        if filters is not None and not isinstance(filters, dict):
            raise ValueError("filters must be a dictionary or None.")

        query = f"""
            SELECT
                chunk_id,
                document_id,
                source,
                page,
                text,
                metadata,
                1 - (embedding <=> %s::vector) AS score
            FROM {self.TABLE_NAME}
            WHERE strategy = %s
        """

        params: list[Any] = [
            self._vector_literal(query_vector),
            strategy,
        ]

        if filters:
            try:
                filters_json = json.dumps(
                    filters,
                    ensure_ascii=False,
                    allow_nan=False,
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid metadata filters.") from exc

            query += " AND metadata @> %s::jsonb"
            params.append(filters_json)

        query += """
            ORDER BY embedding <=> %s::vector ASC, chunk_id ASC
            LIMIT %s;
        """

        # The query vector is used again for cosine-distance ranking.
        params.extend([
            self._vector_literal(query_vector),
            top_k,
        ])

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return [
            {
                "chunk_id": row[0],
                "document_id": row[1],
                "source": row[2],
                "page": row[3],
                "text": row[4],
                "metadata": row[5],
                "score": float(row[6]),
            }
            for row in rows
        ]


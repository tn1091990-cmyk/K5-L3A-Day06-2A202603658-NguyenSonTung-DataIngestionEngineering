"""Choose a real embedding provider (API or local) and implement this contract."""
"""Embedding provider adapter for a local llama.cpp server.

Uses llama.cpp's OpenAI-compatible http://127.0.0.1:9931/v1/embeddings endpoint.
"""
import math
import os
import openai

from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Generate embeddings through an OpenAI-compatible endpoint."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

        self.client = openai.OpenAI(
            base_url=os.getenv(
                "LLAMA_CPP_BASE_URL",
                "http://127.0.0.1:9931/v1",
            ),
            api_key=os.getenv("LLAMA_CPP_API_KEY", "not-needed"),
        )

        self.batch_size = int(
            os.getenv("LLAMA_CPP_BATCH_SIZE", "32")
        )

        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive.")

        # Discover dimensions from a real embedding.
        probe = self._request_embeddings(["dimension detection"])
        self.dimensions = len(probe[0])


    def _request_embeddings(self,  texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts,
            encoding_format="float",
        )

        items = sorted(response.data, key=lambda item: item.index)

        if len(items) != len(texts):
            raise RuntimeError("Embedding response count mismatch.")

        vectors = []

        for index, item in enumerate(items):
            if item.index != index:
                raise RuntimeError("Embedding response order is invalid.")

            vector = item.embedding

            if not vector:
                raise ValueError("Received an empty embedding.")

            if not all(math.isfinite(value) for value in vector):
                raise ValueError("Embedding contains invalid values.")

            vectors.append(vector)

        return vectors

    
    def _validate_vectors( self,  vectors: list[list[float]], ) -> list[list[float]]:
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ValueError(
                    f"Expected {self.dimensions} dimensions, "
                    f"received {len(vector)}."
                )
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        #raise NotImplementedError("TODO: embed_documents")
        """Embed multiple documents, preserving their original order."""
        if any(not isinstance(t, str) or not t.strip() for t in texts):
            raise ValueError("Document texts must be non-empty strings.")
        results = []

        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            results.extend(self._request_embeddings(batch))

        return self._validate_vectors(results)


    def embed_query(self, question: str) -> list[float]:
        #raise NotImplementedError("TODO: embed_query")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must be a non-empty string.")

        vector = self._request_embeddings([question])[0]
        self._validate_vectors([vector])

        return vector

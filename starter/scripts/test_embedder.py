import os
from dotenv import load_dotenv

from src.embeddings import MyEmbedder

load_dotenv()

model_name = os.getenv("EMBEDDING_MODEL")

if not model_name:
    raise ValueError("EMBEDDING_MODEL is missing from .env")

embedder = MyEmbedder(model_name=model_name)

print("Model:", embedder.model_name)
print("Dimensions:", embedder.dimensions)

# Test document embeddings
documents = [
    "AMD Ryzen 7 9700X has 8 cores.",
    "AMD Ryzen 9 9950X has 16 cores."
]

vectors = embedder.embed_documents(documents)

print("Document count:", len(vectors))
print("Vector dimensions:", [len(v) for v in vectors])

# Test query embedding
query_vector = embedder.embed_query(
    "How many cores does Ryzen 7 9700X have?"
)

print("Query dimensions:", len(query_vector))

assert len(vectors) == 2
assert all(len(v) == embedder.dimensions for v in vectors)
assert len(query_vector) == embedder.dimensions

print("\nAll embedding tests passed!")
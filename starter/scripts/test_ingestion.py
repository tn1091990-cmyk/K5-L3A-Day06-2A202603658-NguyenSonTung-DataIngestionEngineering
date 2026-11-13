from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from src.ingestion import load_html_directory


data_dir = Path(__file__).resolve().parents[1] / "data"

documents = load_html_directory(data_dir)

print("\n========== INGESTION SUMMARY ==========")
print("Documents loaded:", len(documents))

total_characters = 0
empty_documents = []

for document in documents:
    count = len(document.text)
    total_characters += count

    print(
        f"{document.document_id}: "
        f"{count:,} characters | "
        f"{document.metadata['extraction_status']}"
    )

    if not document.text:
        empty_documents.append(document.document_id)

print("---------------------------------------")
print("Total characters:", f"{total_characters:,}")
print("Empty documents:", len(empty_documents))

if empty_documents:
    print("Empty document IDs:", empty_documents)

if len(documents) < 30:
    print("WARNING: Expected 30 or more HTML documents.")

print("=======================================")
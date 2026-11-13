
from src.ingestion import load_html
import re
from src.models import DocumentPage
from pathlib import Path


print("Working directory:", Path.cwd())
print("Data folder exists:", Path("data").exists())
print("HTML files:", list(Path("data").glob("*.html"))[:5])
page = load_html(
    "data/AMD Ryzen 7 7800X3D.html",
    document_id="amd-ryzen-7-7800x3d",
)
from src.metadata_cpu import enrich_cpu_metadata
enriched = enrich_cpu_metadata(page)

print("\n--- Enriched CPU Metadata ---")
for key, value in enriched.metadata.items():
    print(f"{key}: {value}")

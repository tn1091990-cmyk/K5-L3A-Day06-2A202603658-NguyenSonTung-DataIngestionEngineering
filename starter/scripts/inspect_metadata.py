from pathlib import Path
from src.ingestion import load_html_directory

documents = load_html_directory(Path("data"))

target = "amd-ryzen-7-7800x3d"

doc = next(
    (d for d in documents if d.document_id == target),
    None,
)

if doc is None:
    raise ValueError(f"Document not found: {target}")

keywords = [
    "Socket:",
    "Codename:",
    "Process Size:",
    "Frequency:",
    "TDP:",
    "Cache L1:",
    "Cache L2:",
    "Cache L3:",
    "Memory",
    "Rated Speed:",
    "# of Cores:",
    "# of Threads:",
    "Release Date:",
]

lines = doc.text.splitlines()

for i, line in enumerate(lines):
    if any(keyword.lower() in line.lower() for keyword in keywords):
        print(f"\nLine {i}:")
        for j in range(i, min(i + 5, len(lines))):
            print(f"  {j}: {lines[j]!r}")
        for i in range(268, 278):
            print(i, repr(lines[i]))
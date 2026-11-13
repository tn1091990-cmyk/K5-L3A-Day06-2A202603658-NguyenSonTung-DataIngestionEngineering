
from pathlib import Path

from src.ingestion import load_html
from src.metadata_cpu import enrich_cpu_metadata


DATA_DIR = Path("data")

REQUIRED_FIELDS = [
    "series",
    "architecture",
    "socket",
    "codename",
    "process_nm",
    "tdp_w",
    "cores",
    "threads",
    "ecc_memory",
]


def main():
    html_files = sorted(DATA_DIR.glob("*.html"))

    print(f"Found {len(html_files)} HTML files\n")

    if not html_files:
        print("ERROR: No HTML files found.")
        return

    total_success = 0
    total_missing = 0

    for file_path in html_files:
        document_id = file_path.stem

        page = load_html(
            str(file_path),
            document_id=document_id,
        )

        enriched = enrich_cpu_metadata(page)

        missing = [
            field
            for field in REQUIRED_FIELDS
            if enriched.metadata.get(field) is None
        ]

        if not missing:
            total_success += 1
            status = "PASS"
        else:
            total_missing += 1
            status = "MISSING: " + ", ".join(missing)

        print(f"[{status}] {file_path.name}")

        print(
            f"    Series: {enriched.metadata.get('series')}, "
            f"Architecture: {enriched.metadata.get('architecture')}, "
            f"Cores: {enriched.metadata.get('cores')}, "
            f"TDP: {enriched.metadata.get('tdp_w')} W"
        )

    print("\n========== SUMMARY ==========")
    print(f"Total documents: {len(html_files)}")
    print(f"Passed: {total_success}")
    print(f"Missing required metadata: {total_missing}")


if __name__ == "__main__":
    main()

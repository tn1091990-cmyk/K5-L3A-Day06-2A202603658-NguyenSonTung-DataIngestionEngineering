"""Extract CPU-specific metadata from TechPowerUp HTML text."""

import re

from models import DocumentPage


def _extract_field(text: str, label: str) -> str | None:
    """Extract a field value from TechPowerUp's extracted HTML text."""

    lines = text.splitlines()

    for i, line in enumerate(lines):
        current = line.strip()

        # Match the requested label.
        if not re.match(rf"^{re.escape(label)}\s*:", current, re.I):
            continue

        # Case 1: Label and value on the same line.
        # Example: Process Size: | 5 nm
        value = current.split(":", 1)[1].strip()
        if value:
            value = value.lstrip("|").strip()
            if value:
                return value

        # Case 2 and 3: Look at following lines.
        for next_line in lines[i + 1:i + 5]:
            candidate = next_line.strip()

            if not candidate:
                continue

            # Skip a standalone separator.
            if candidate == "|":
                continue

            # Remove a leading separator.
            candidate = candidate.lstrip("|").strip()

            if not candidate:
                continue

            # Stop if we reach another field label.
            if re.match(r"^[^|]+:\s*(?:\||$)", candidate):
                break

            return candidate

    return None


def _number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def enrich_cpu_metadata(page: DocumentPage) -> DocumentPage:
    text = page.text
    metadata = page.metadata.copy()

    # Generation contains both Ryzen series and Zen architecture.
    generation = _extract_field(text, "Generation")

    if generation:
        series_match = re.search(r"\bRyzen\s+\d+\b", generation, re.I)
        architecture_match = re.search(r"\bZen\s+\d+\b", generation, re.I)

        if series_match:
            metadata["series"] = series_match.group().title()
            architecture_match = re.search(
                r"\(Zen\s+\d+",
                text[text.find("Generation:"):text.find("Memory Support:")],
                re.I
            )
        if architecture_match:
            metadata["architecture"] = architecture_match.group().lstrip("(").title()

    # Text fields.
    text_fields = {
        "socket": "Socket",
        "codename": "Codename",
        "released": "Release Date",
        "memory_type": "Memory Support",
        "memory_channels": "Memory Bus",
        "memory_bandwidth": "Memory Bandwidth",
        "cache_l1": "Cache L1",
        "cache_l2": "Cache L2",
        "cache_l3": "Cache L3",
    }

    for key, label in text_fields.items():
        value = _extract_field(text, label)
        if value:
            metadata[key] = value

    # Numeric fields.
    numeric_fields = {
        "process_nm": "Process Size",
        "base_clock_ghz": "Frequency",
        "boost_clock_ghz": "Turbo Clock",
        "tdp_w": "TDP",
        "memory_speed_mts": "Rated Speed",
        "cores": "# of Cores",
        "threads": "# of Threads",
    }

    for key, label in numeric_fields.items():
        value = _extract_field(text, label)
        number = _number(value)
        if number is not None:
            metadata[key] = int(number) if number.is_integer() else number

    # Boolean field.
    ecc = _extract_field(text, "ECC Memory")
    if ecc:
        if ecc.lower() in {"yes", "supported"}:
            metadata["ecc_memory"] = True
        elif ecc.lower() in {"no", "unsupported"}:
            metadata["ecc_memory"] = False

    return DocumentPage(
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=page.text,
        metadata=metadata,
    )

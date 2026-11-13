
"""Implement fixed-size and structure-aware chunking."""
from models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split text into overlapping windows and retain page metadata."""
    if size <= 0:
        raise ValueError("size must be greater than 0")

    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    text = page.text
    if not text:
        return []

    chunks = []
    step = size - overlap

    for start in range(0, len(text), step):
        chunk_text = text[start:start + size]

        if not chunk_text:
            break

        chunk_id = f"{page.document_id}-p{page.page}-fixed-{len(chunks)}"

        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=page.metadata.copy(),
            )
        )

        if start + size >= len(text):
            break

    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be greater than 0")

    if not page.text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in page.text.split("\n\n")
        if paragraph.strip()
    ]

    chunks = []
    current_parts = []
    current_length = 0

    def add_chunk(text: str) -> None:
        chunk_id = f"{page.document_id}-p{page.page}-paragraph-{len(chunks)}"

        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=text,
                metadata=page.metadata.copy(),
            )
        )

    for paragraph in paragraphs:
        # Split paragraphs that exceed the maximum size.
        if len(paragraph) > max_size:
            if current_parts:
                add_chunk("\n\n".join(current_parts))
                current_parts = []
                current_length = 0

            for start in range(0, len(paragraph), max_size):
                piece = paragraph[start:start + max_size]
                add_chunk(piece)

            continue

        separator_length = 2 if current_parts else 0
        proposed_length = current_length + separator_length + len(paragraph)

        if proposed_length > max_size:
            add_chunk("\n\n".join(current_parts))
            current_parts = [paragraph]
            current_length = len(paragraph)
        else:
            current_parts.append(paragraph)
            current_length = proposed_length

    if current_parts:
        add_chunk("\n\n".join(current_parts))

    return chunks

from src.chunking import fixed_size, by_paragraph
from src.models import DocumentPage


page = DocumentPage(
    document_id="test-document",
    source="test.html",
    page=1,
    text=(
        "Paragraph one contains some information.\n\n"
        "Paragraph two contains additional information.\n\n"
        "Paragraph three contains more details."
    ),
    metadata={"format": "html"}
)

long_page = DocumentPage(
    document_id="long-test",
    source="long.html",
    page=1,
    text="A" * 150,
    metadata={}
)


# Test A: Fixed-size chunking
fixed_chunks = fixed_size(page, size=50, overlap=10)
long_chunks = by_paragraph(long_page, max_size=60)

print("Fixed-size chunks:")
for chunk in fixed_chunks:
    print(chunk.chunk_id, len(chunk.text), repr(chunk.text))

# Test B: Paragraph-based chunking
paragraph_chunks = by_paragraph(page, max_size=60)

print("\nParagraph chunks:")
for chunk in paragraph_chunks:
    print(chunk.chunk_id, len(chunk.text), repr(chunk.text))



# Basic assertions
assert all(chunk.document_id == page.document_id for chunk in fixed_chunks)
assert all(chunk.source == page.source for chunk in paragraph_chunks)
assert all(chunk.metadata == page.metadata for chunk in fixed_chunks)
assert all(len(chunk.text) <= 60 for chunk in paragraph_chunks)

print("\nAll basic checks passed!")


print("\nOversized paragraph test:")
for chunk in long_chunks:
    print(len(chunk.text))

assert [len(c.text) for c in long_chunks] == [60, 60, 30]
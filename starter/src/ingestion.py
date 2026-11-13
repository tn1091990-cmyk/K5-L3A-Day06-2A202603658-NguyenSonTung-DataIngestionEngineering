"""Read and normalize HTML/PDF source data."""
import re
import unicodedata
import traceback
from pypdf import PdfReader
from models import DocumentPage
from pathlib import Path
from html.parser import HTMLParser
from html import unescape

class HTMLTextExtractor(HTMLParser):
    """Extract readable HTML content while preserving basic structure."""

    BLOCK_TAGS = {
        "p", "div", "section", "article", "main",
        "header", "footer", "h1", "h2", "h3",
        "h4", "h5", "h6", "ul", "ol", "li",
        "table", "tr", "blockquote", "pre",
    }

    IGNORED_TAGS = {
        "script", "style", "noscript", "svg",
        "iframe", "nav", "footer",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored_depth = 0
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag in self.IGNORED_TAGS:
            self.ignored_depth += 1
            return

        if self.ignored_depth:
            return

        if tag == "title":
            self.in_title = True

        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

        if tag == "br":
            self.parts.append("\n")

        if tag == "td":
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in self.IGNORED_TAGS and self.ignored_depth:
            self.ignored_depth -= 1
            return

        if self.ignored_depth:
            return

        if tag == "title":
            self.in_title = False

        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.ignored_depth:
            return

        if self.in_title:
            self.title += data
        else:
            self.parts.append(data)

    def get_text(self):
        return normalize_text("".join(self.parts))


def make_document_id(filename: str) -> str:
    """Create a stable document ID from a filename."""
    import re

    return re.sub(
        r"[^a-z0-9]+",
        "-",
        filename.lower()
    ).strip("-")

def load_pdf(path: Path, document_id: str, source: str,) -> list[DocumentPage]:
    """Extract each physical PDF page."""

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    reader = PdfReader(str(path))
    documents = []

    for index, pdf_page in enumerate(reader.pages):
        page_number = index + 1

        try:
            text = normalize_text(
                pdf_page.extract_text() or ""
            )

            metadata = {
                "source_path": str(path),
                "source_unit_type": "pdf_page",
                "character_count": len(text),
                "extraction_status": "success" if text else "empty",
            }

        except Exception as error:
            text = ""
            metadata = {
                "source_path": str(path),
                "source_unit_type": "pdf_page",
                "character_count": 0,
                "extraction_status": "error",
                "error": str(error),
            }

        documents.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_number,
                text=text,
                metadata=metadata,
            )
        )

    return documents



def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without discarding structure."""

    text = unicodedata.normalize("NFC", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")

    # Collapse horizontal whitespace.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces around line breaks.
    text = re.sub(r" *\n *", "\n", text)

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def load_html(path: Path, document_id: str, source: str | None = None,) -> DocumentPage:
    """Load one HTML document."""

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    html = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    parser = HTMLTextExtractor()
    parser.feed(html)
    parser.close()

    text = parser.get_text()
    title = normalize_text(parser.title)

    return DocumentPage(
        document_id=document_id,
        source=source or str(path),
        page=1,
        text=text,
        metadata={
            "title": title or path.stem,
            "source_path": str(path),
            "source_unit_type": "html_document",
            "character_count": len(text),
            "extraction_status": "success" if text else "empty",
        },
    )


def load_html_directory(directory: Path) -> list[DocumentPage]:
    """Load all HTML documents from a directory."""

    directory = Path(directory)

    if not directory.is_dir():
        raise NotADirectoryError(directory)

    documents = []

    html_files = sorted(
        list(directory.glob("*.html"))
        + list(directory.glob("*.htm"))
    )

    for path in html_files:
        try:
            document = load_html(
                path=path,
                document_id=make_document_id(path.stem),
            )

            documents.append(document)

            if not document.text:
                print(f"WARNING: Empty HTML document: {path}")

        except Exception as error:
           # print(f"ERROR: Failed to process {path}: {error}")
            print(f"\nERROR processing: {path}")
            traceback.print_exc()

    return documents
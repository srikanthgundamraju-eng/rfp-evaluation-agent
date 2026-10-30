
from io import BytesIO

from pypdf import PdfReader


def extract_pdf_pages(pdf_bytes: bytes) -> list[dict]:
    """Extract text from a PDF while preserving its original page numbers."""
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()

        if text:
            pages.append({
                "page_number": page_number,
                "text": text,
            })

    if not pages:
        raise ValueError(
            "No extractable text found in PDF. "
            "It may be scanned or image-only."
        )

    return pages


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract and combine PDF text for existing callers."""
    pages = extract_pdf_pages(pdf_bytes)
    return "\n\n".join(page["text"] for page in pages)

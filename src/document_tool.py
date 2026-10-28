from io import BytesIO
from pypdf import PdfReader

def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError("No extractable text found in PDF. It may be scanned or image-only.")
    return text

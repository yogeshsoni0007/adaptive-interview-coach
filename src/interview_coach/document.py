from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


class DocumentError(ValueError):
    """Raised when an uploaded document cannot provide usable text."""


def extract_text(filename: str, content: bytes) -> str:
    if not content:
        raise DocumentError(f"{filename} is empty.")

    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        elif suffix == ".docx":
            document = Document(BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        elif suffix == ".txt":
            text = content.decode("utf-8")
        else:
            raise DocumentError(f"Unsupported file type: {suffix or 'unknown'}.")
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError(f"Could not read {filename}. Verify that the file is not damaged.") from exc

    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not cleaned:
        raise DocumentError(
            f"No readable text was found in {filename}. Scanned PDFs require OCR, which is not part of Version 1."
        )
    return cleaned

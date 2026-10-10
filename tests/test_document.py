from io import BytesIO

import pytest
from docx import Document

from interview_coach.document import DocumentError, extract_text


def test_extracts_text_file() -> None:
    assert extract_text("role.txt", b"Risk analyst with payments experience") == (
        "Risk analyst with payments experience"
    )


def test_extracts_docx_file() -> None:
    document = Document()
    document.add_paragraph("Payments product manager")
    buffer = BytesIO()
    document.save(buffer)

    assert extract_text("resume.docx", buffer.getvalue()) == "Payments product manager"


def test_rejects_empty_file() -> None:
    with pytest.raises(DocumentError, match="empty"):
        extract_text("resume.pdf", b"")


def test_rejects_unsupported_file() -> None:
    with pytest.raises(DocumentError, match="Unsupported"):
        extract_text("resume.png", b"image")

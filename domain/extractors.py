from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from domain.text import normalize_text


class UnsupportedDocumentError(RuntimeError):
    pass


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    page_text = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    return normalize_text("\n\n".join(page_text))


def extract_text_from_download(path: Path, content_type: str | None = None) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf":
        return extract_text_from_pdf(path)
    if suffix in {".txt", ".text"} or (content_type or "").startswith("text/"):
        return normalize_text(path.read_text(encoding="utf-8", errors="replace"))
    raise UnsupportedDocumentError(
        f"Unsupported document type for {path.name}. Add a converter in domain/extractors.py."
    )

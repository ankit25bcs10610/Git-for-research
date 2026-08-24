import io
import json

import pdfplumber

from app.ingestion.base import ParsedArtifact


def parse_pdf(file_bytes: bytes, filename: str) -> ParsedArtifact:
    pages = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": page_number, "text": text})

    content = json.dumps(pages)
    return ParsedArtifact(artifact_type="pdf", name=filename, content=content)

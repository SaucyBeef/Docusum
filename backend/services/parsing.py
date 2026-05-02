from io import BytesIO


def extract_text(filename: str, content_type: str | None, file_bytes: bytes) -> str:
    lower_name = filename.lower()
    normalized_content_type = (content_type or "").lower()

    if lower_name.endswith(".txt") or lower_name.endswith(".md") or "text/plain" in normalized_content_type:
        text = file_bytes.decode("utf-8", errors="ignore")
        return _normalize_text(text)

    if lower_name.endswith(".pdf") or "application/pdf" in normalized_content_type:
        return _extract_pdf_text(file_bytes)

    if lower_name.endswith(".docx") or "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in normalized_content_type:
        return _extract_docx_text(file_bytes)

    raise ValueError("Unsupported file type. Allowed: .txt, .md, .pdf, .docx")


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("pypdf is required for PDF uploads.") from exc

    reader = PdfReader(BytesIO(file_bytes))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    text = _normalize_text(text)
    if not text:
        raise ValueError("No readable text found in PDF.")
    return text


def _extract_docx_text(file_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("python-docx is required for DOCX uploads.") from exc

    doc = Document(BytesIO(file_bytes))
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    text = _normalize_text(text)
    if not text:
        raise ValueError("No readable text found in DOCX.")
    return text


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]

    compact_lines: list[str] = []
    last_blank = False
    for line in lines:
        if line:
            compact_lines.append(line)
            last_blank = False
        elif not last_blank:
            compact_lines.append("")
            last_blank = True

    return "\n".join(compact_lines).strip()

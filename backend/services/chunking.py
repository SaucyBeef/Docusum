def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    clean_text = text.strip()
    if not clean_text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(clean_text)

    while start < text_len:
        end = min(text_len, start + chunk_size)
        if end < text_len:
            boundary = _find_split_boundary(clean_text, start, end)
            if boundary > start:
                end = boundary

        chunk = clean_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = max(0, end - overlap)

    return _dedupe_consecutive_chunks(chunks)


def _find_split_boundary(text: str, start: int, end: int) -> int:
    newline_boundary = text.rfind("\n", start, end)
    space_boundary = text.rfind(" ", start, end)
    return max(newline_boundary, space_boundary)


def _dedupe_consecutive_chunks(chunks: list[str]) -> list[str]:
    deduped: list[str] = []
    previous = None
    for chunk in chunks:
        if chunk != previous:
            deduped.append(chunk)
            previous = chunk
    return deduped

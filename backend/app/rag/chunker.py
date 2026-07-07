"""Recursive text splitter with sentence boundary awareness."""

import re

_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]


def _split_by_separator(text: str, separator: str) -> list[str]:
    """Split text by separator, keeping the separator at the end of each piece."""
    if not separator:
        return list(text)
    parts = text.split(separator)
    result: list[str] = []
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            result.append(part + separator)
        elif part:
            result.append(part)
    return result


def _merge_pieces(pieces: list[str], chunk_size: int, overlap: int) -> list[str]:
    """Merge small pieces into chunks respecting size and overlap."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for piece in pieces:
        piece_len = len(piece)
        if current_len + piece_len > chunk_size and current:
            chunks.append("".join(current).strip())
            overlap_pieces: list[str] = []
            overlap_len = 0
            for p in reversed(current):
                if overlap_len + len(p) > overlap:
                    break
                overlap_pieces.insert(0, p)
                overlap_len += len(p)
            current = overlap_pieces
            current_len = overlap_len

        current.append(piece)
        current_len += piece_len

    if current:
        merged = "".join(current).strip()
        if merged:
            chunks.append(merged)

    return chunks


def _recursive_split(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    """Recursively split text using progressively finer separators."""
    if len(text) <= chunk_size:
        return [text]

    sep = ""
    remaining_seps = separators
    for i, s in enumerate(separators):
        if s in text:
            sep = s
            remaining_seps = separators[i + 1 :]
            break

    pieces = _split_by_separator(text, sep)

    result: list[str] = []
    for piece in pieces:
        if len(piece) <= chunk_size:
            result.append(piece)
        elif remaining_seps:
            result.extend(_recursive_split(piece, chunk_size, remaining_seps))
        else:
            result.append(piece)

    return result


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
    separators: list[str] | None = None,
) -> list[str]:
    """Split text into overlapping chunks using recursive sentence-aware splitting.

    Tries separators in order: paragraph → newline → sentence → clause → word → char.
    Respects sentence boundaries when possible.

    Args:
        text: The full text to split.
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters to overlap between consecutive chunks.
        separators: Custom separator hierarchy (defaults to built-in list).

    Returns:
        List of non-empty text chunks.
    """
    if not text or not text.strip():
        return []
    if chunk_size <= 0:
        return [text.strip()]

    text = re.sub(r"\n{3,}", "\n\n", text)

    seps = separators if separators is not None else _SEPARATORS
    pieces = _recursive_split(text, chunk_size, seps)
    chunks = _merge_pieces(pieces, chunk_size, overlap)

    return [c for c in chunks if c]

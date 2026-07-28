"""Context builder — structured context assembly with per-section token budgets."""

import logging
from typing import Any

import tiktoken

from app.core.config import settings

logger = logging.getLogger(__name__)

_ENCODING: tiktoken.Encoding | None = None

_SYSTEM_INSTRUCTION = (
    "You are a helpful assistant. Answer the user's question based on the provided context. "
    "If the context doesn't contain relevant information, say so clearly. "
    "Cite the document source when using information from the context."
)


def _get_encoding() -> tiktoken.Encoding:
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")
    return _ENCODING


def count_tokens(text: str) -> int:
    """Count tokens in a text string."""
    return len(_get_encoding().encode(text))


def build_context(
    retrieved_chunks: list[dict[str, Any]],
    chat_history: list[dict[str, str]],
    max_context_tokens: int | None = None,
    max_history_tokens: int | None = None,
    history_turns: int | None = None,
) -> list[dict[str, str]]:
    """Build structured message list with per-section token budgets.

    Token budget allocation:
    - System instruction: ~50 tokens (fixed)
    - Retrieved documents: CONTEXT_MAX_TOKENS (default 3000)
    - Conversation history: remaining budget, trimmed to N turns

    Message structure:
    1. System: instruction + retrieved document context (with metadata)
    2. Conversation history (last N turns, token-trimmed)
    """
    ctx_budget = max_context_tokens or settings.CONTEXT_MAX_TOKENS
    max_turns = history_turns or settings.CONTEXT_HISTORY_TURNS

    messages: list[dict[str, str]] = []

    doc_context = _build_document_context(retrieved_chunks, ctx_budget)
    if doc_context:
        system_content = f"{_SYSTEM_INSTRUCTION}\n\n---\n\n{doc_context}"
    else:
        system_content = _SYSTEM_INSTRUCTION

    messages.append({"role": "system", "content": system_content})

    history_budget = max_history_tokens or (ctx_budget * 2)
    trimmed_history = _trim_history(chat_history, max_turns, history_budget)
    messages.extend(trimmed_history)

    return messages


def _build_document_context(
    chunks: list[dict[str, Any]],
    max_tokens: int,
) -> str:
    """Build structured context from retrieved chunks with metadata."""
    if not chunks:
        return ""

    parts: list[str] = []
    tokens_used = 0
    header = "## Retrieved Documents\n"
    tokens_used += count_tokens(header)

    for i, chunk in enumerate(chunks, 1):
        payload = chunk.get("payload") or {}
        title = payload.get("title", "Unknown")
        content = payload.get("content", "")
        document_id = payload.get("document_id", "")
        chunk_index = payload.get("chunk_index", "")
        score = chunk.get("score", 0.0)

        metadata_line = f"[Source: {title}"
        if document_id:
            metadata_line += f" | doc_id: {document_id}"
        if chunk_index != "":
            metadata_line += f" | chunk: {chunk_index}"
        if score:
            metadata_line += f" | relevance: {score:.3f}"
        metadata_line += "]"

        part = f"### [{i}] {title}\n{metadata_line}\n{content}"
        part_tokens = count_tokens(part)

        if tokens_used + part_tokens > max_tokens:
            remaining = max_tokens - tokens_used
            if remaining > 50:
                truncated = _truncate_to_tokens(part, remaining)
                parts.append(truncated)
            break

        parts.append(part)
        tokens_used += part_tokens

    if not parts:
        return ""

    return header + "\n\n".join(parts)


def _trim_history(
    chat_history: list[dict[str, str]],
    max_turns: int,
    max_tokens: int,
) -> list[dict[str, str]]:
    """Trim history to last N turns AND within token budget."""
    max_messages = max_turns * 2
    recent = chat_history[-max_messages:] if len(chat_history) > max_messages else chat_history

    tokens_used = 0
    result: list[dict[str, str]] = []
    for msg in reversed(recent):
        msg_tokens = count_tokens(msg["content"])
        if tokens_used + msg_tokens > max_tokens:
            break
        result.append(msg)
        tokens_used += msg_tokens

    result.reverse()
    return result


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget."""
    enc = _get_encoding()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated: str = enc.decode(tokens[:max_tokens])
    return truncated + "..."

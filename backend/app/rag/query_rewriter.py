"""Query rewriter — contextualize multi-turn queries into standalone form."""

import logging

from app.core.config import settings
from app.services.llm import llm_service

logger = logging.getLogger(__name__)

_REWRITE_PROMPT = (
    "Given the following conversation history and a follow-up question, "
    "rewrite the follow-up question as a standalone question that captures "
    "all necessary context. Do NOT answer the question — only rewrite it.\n"
    "If the question is already standalone, return it unchanged.\n\n"
    "Chat history:\n{history}\n\n"
    "Follow-up question: {question}\n\n"
    "Standalone question:"
)


def _format_history(messages: list[dict[str, str]], max_turns: int = 6) -> str:
    """Format recent conversation history for the rewriter prompt."""
    recent = messages[-(max_turns * 2) :]
    lines: list[str] = []
    for msg in recent:
        role = msg["role"].capitalize()
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


async def rewrite_query(
    query: str,
    chat_history: list[dict[str, str]],
) -> str:
    """Rewrite a follow-up query into a standalone question using conversation context.

    Falls back to the original query on failure or if disabled.
    """
    if not settings.QUERY_REWRITER_ENABLED:
        return query

    user_messages = [m for m in chat_history if m["role"] in ("user", "assistant")]
    if len(user_messages) <= 1:
        return query

    history_text = _format_history(user_messages, max_turns=settings.CONTEXT_HISTORY_TURNS)

    try:
        response = await llm_service.chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": _REWRITE_PROMPT.format(history=history_text, question=query),
                }
            ],
            temperature=0.0,
            max_tokens=200,
        )
        rewritten = (response["content"] or "").strip()
        if not rewritten:
            return query
        logger.debug("Query rewritten: '%s' -> '%s'", query, rewritten)
        return rewritten
    except Exception as e:
        logger.warning("Query rewrite failed, using original: %s", e)
        return query

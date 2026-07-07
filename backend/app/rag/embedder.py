"""OpenAI embedding wrapper with retry logic."""

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def embed_texts(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    Args:
        texts: List of texts to embed.
        model: Embedding model override (defaults to config).

    Returns:
        List of embedding vectors.
    """
    client = _get_client()
    response = await client.embeddings.create(
        model=model or settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


async def embed_query(text: str, model: str | None = None) -> list[float]:
    """Generate embedding for a single query text.

    Args:
        text: Query text to embed.
        model: Embedding model override.

    Returns:
        Embedding vector.
    """
    embeddings = await embed_texts([text], model)
    return embeddings[0]

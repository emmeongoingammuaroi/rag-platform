"""OpenAI LLM service — chat completions, streaming, and embeddings."""

import logging
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Async wrapper around OpenAI's chat and embedding APIs with retry logic."""

    def __init__(self) -> None:
        """Initialize the OpenAI async client with settings from config."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate chat completion.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model to use (defaults to config)

        Returns:
            Chat completion response
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or settings.OPENAI_MAX_TOKENS,
            )

            return {
                "id": response.id,
                "model": response.model,
                "content": response.choices[0].message.content,
                "role": response.choices[0].message.role,
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming chat completion.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model to use (defaults to config)

        Yields:
            Streamed content chunks
        """
        try:
            stream = await self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or settings.OPENAI_MAX_TOKENS,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Streaming chat completion error: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def create_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model to use (defaults to config)

        Returns:
            List of embedding vectors
        """
        try:
            response = await self.client.embeddings.create(
                model=model or self.embedding_model,
                input=texts,
            )

            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise

    async def create_single_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            model: Embedding model to use (defaults to config)

        Returns:
            Embedding vector
        """
        embeddings = await self.create_embeddings([text], model)
        embedding: list[float] = embeddings[0]
        return embedding


llm_service = AIService()

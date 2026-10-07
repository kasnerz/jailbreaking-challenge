import re
from typing import Any, AsyncGenerator, Dict, List

from openai import AsyncOpenAI

from .config import settings


def _get_client(timeout: float = 60.0, max_retries: int = 2) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.CHAT_EINFRA_URL,
        api_key=settings.CHAT_EINFRA_KEY or "none",
        timeout=timeout,
        max_retries=max_retries,
    )


def check_success(response_text: str, secret_word: str) -> bool:
    """Case-insensitive check if secret word appears in the response."""
    pattern = re.compile(re.escape(secret_word), re.IGNORECASE)
    return bool(pattern.search(response_text))


async def stream_chat(
    system_prompt: str,
    messages: List[Dict[str, Any]],
) -> AsyncGenerator[str, None]:
    """
    Stream chat completion tokens. Yields token delta strings.
    The caller is responsible for detecting success on the accumulated text.
    """
    client = _get_client()
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    stream = await client.chat.completions.create(
        model=settings.MODEL_NAME,
        messages=full_messages,
        stream=True,
        max_tokens=512,
        temperature=0.7,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def health_check() -> bool:
    """Check if the configured OpenAI-compatible endpoint is reachable."""
    try:
        # GET {base_url}/models; raises on connection errors and non-2xx.
        async with _get_client(timeout=5.0, max_retries=0) as client:
            await client.models.list()
        return True
    except Exception:
        return False

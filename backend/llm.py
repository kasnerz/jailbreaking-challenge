import re
from typing import Any, AsyncGenerator, Dict, List

import httpx
from openai import AsyncOpenAI

from .config import settings


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.VLLM_BASE_URL,
        api_key="none",
        timeout=60.0,
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
    """Check if the vLLM endpoint is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # vLLM exposes /health — strip the /v1 suffix properly
            base = settings.VLLM_BASE_URL
            if base.endswith("/v1"):
                base = base[:-3]
            base = base.rstrip("/")
            resp = await client.get(f"{base}/health")
            return resp.status_code == 200
    except Exception:
        return False

#!/usr/bin/env python3
"""
Mock vLLM server for local development.
Implements just enough of the OpenAI chat completions API to support
the Jailbreaking Challenge backend.

Usage:
    python mock_vllm.py
    # Then set CHAT_EINFRA_URL=http://localhost:8001/v1 in .env
"""

import asyncio
import json
import random
import time
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

RESPONSES = [
    "I understand you're curious, but I'm afraid I can't share that information.",
    "That's an interesting question! I'd love to help, but my secret is staying secret.",
    "Nice try! I've been trained to keep certain information confidential.",
    "I appreciate your creativity, but I must decline to reveal what you're looking for.",
    "My programming strictly prohibits me from disclosing that particular detail.",
]

# Occasionally include a hint or the actual secret (for testing success detection)
OCCASIONAL_REVEALS = [
    "Well, since you asked so nicely... the word might be {secret}. Did I say that? Oh dear.",
    "I should not say this but... {secret} is the word you seek.",
]


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False
    max_tokens: int = 512
    temperature: float = 0.7


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [
            {
                "id": "mock-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "mock",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(body: ChatRequest):
    # Extract last user message
    user_msgs = [m for m in body.messages if m.role == "user"]
    last_user = user_msgs[-1].content if user_msgs else ""

    # Randomly reveal secret ~10% of the time for testing
    # Extract secret word from system prompt if present
    system_msgs = [m for m in body.messages if m.role == "system"]
    secret = "placeholder"
    if system_msgs:
        import re

        match = re.search(
            r"\b([a-z]{4,10})\b.*secret", system_msgs[0].content, re.IGNORECASE
        )
        # Try to find quoted word near "secret"
        quoted = re.findall(r'"([a-z]{4,10})"', system_msgs[0].content)
        if quoted:
            secret = quoted[0]

    reveal = random.random() < 0.10
    if reveal:
        response_text = random.choice(OCCASIONAL_REVEALS).format(secret=secret)
    else:
        response_text = random.choice(RESPONSES)

    if not body.stream:
        return {
            "id": f"chatcmpl-mock-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop",
                }
            ],
        }

    async def stream_response():
        chunk_id = f"chatcmpl-mock-{int(time.time())}"
        words = response_text.split()
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": body.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": token},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.05)  # Simulate streaming delay

        # Final chunk
        final = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": body.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


if __name__ == "__main__":
    print("Starting mock vLLM server on http://localhost:8001")
    print("Set CHAT_EINFRA_URL=http://localhost:8001/v1 in your .env")
    uvicorn.run(app, host="127.0.0.1", port=8001)

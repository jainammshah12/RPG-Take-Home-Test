"""Shared Groq client utilities."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from groq import Groq, RateLimitError

CHAT_MODEL = "llama-3.3-70b-versatile"


def groq_available() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def get_groq_client() -> Groq | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def groq_chat_json(
    system: str,
    user: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> Any:
    """Call Groq and parse a JSON object or array from the reply."""
    client = get_groq_client()
    if client is None:
        return None

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = (response.choices[0].message.content or "").strip()
            return _extract_json(content)
        except RateLimitError:
            if attempt == 0:
                time.sleep(2)
                continue
            return None
        except Exception:
            return None
    return None

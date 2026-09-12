from __future__ import annotations

import json

import httpx

from app.core.settings import settings


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Small OpenAI-compatible chat client.

    This intentionally depends on a generic base URL/model/key so the execution
    worker is not coupled to one model vendor.
    """

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if settings.llm_mode == "mock":
            raise LLMError("LLM_MODE=mock: configure an OpenAI-compatible model endpoint before autonomous patch generation")
        if not settings.llm_base_url or not settings.llm_api_key or not settings.llm_model:
            raise LLMError("LLM_BASE_URL, LLM_API_KEY and LLM_MODEL must be configured")

        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.llm_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": settings.llm_num_predict,
            "options": {"num_ctx": settings.llm_num_ctx, "num_predict": settings.llm_num_predict},
            "keep_alive": settings.llm_keep_alive,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=settings.command_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM response did not contain choices[0].message.content") from exc

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
            raise LLMError("LLM_MODE=mock: configure a model endpoint before autonomous patch generation")
        if settings.llm_mode == "ollama":
            return self._complete_ollama(system_prompt, user_prompt)
        return self._complete_openai(system_prompt, user_prompt)

    def _complete_ollama(self, system_prompt: str, user_prompt: str) -> str:
        if not settings.llm_base_url or not settings.llm_model:
            raise LLMError("LLM_BASE_URL and LLM_MODEL must be configured")
        base = settings.llm_base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        payload = {
            "model": settings.llm_model, "stream": False, "format": "json",
            "keep_alive": settings.llm_keep_alive,
            "options": {"temperature": 0, "num_ctx": settings.llm_num_ctx, "num_predict": settings.llm_num_predict},
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        }
        data = self._post(base + "/api/chat", payload, {})
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError("Ollama response did not contain message.content") from exc

    def _complete_openai(self, system_prompt: str, user_prompt: str) -> str:
        if not settings.llm_base_url or not settings.llm_api_key or not settings.llm_model:
            raise LLMError("LLM_BASE_URL, LLM_API_KEY and LLM_MODEL must be configured")
        payload = {
            "model": settings.llm_model, "temperature": 0,
            "response_format": {"type": "json_object"}, "max_tokens": settings.llm_num_predict,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        }
        data = self._post(settings.llm_base_url.rstrip("/") + "/chat/completions", payload, {"Authorization": f"Bearer {settings.llm_api_key}"})
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM response did not contain choices[0].message.content") from exc

    @staticmethod
    def _post(url: str, payload: dict, headers: dict[str, str]) -> dict:
        try:
            with httpx.Client(timeout=settings.command_timeout_seconds) as client:
                response = client.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

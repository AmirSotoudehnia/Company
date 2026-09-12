from app.agents.llm import LLMClient


def test_ollama_native_payload_honors_memory_controls(monkeypatch):
    import app.agents.llm as mod
    monkeypatch.setattr(mod.settings, "llm_mode", "ollama")
    monkeypatch.setattr(mod.settings, "llm_base_url", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr(mod.settings, "llm_model", "qwen2.5-coder:1.5b")
    monkeypatch.setattr(mod.settings, "llm_num_ctx", 2048)
    monkeypatch.setattr(mod.settings, "llm_num_predict", 1024)
    monkeypatch.setattr(mod.settings, "llm_keep_alive", "0")
    seen = {}
    def fake_post(url, payload, headers):
        seen.update(url=url, payload=payload, headers=headers)
        return {"message": {"content": "{}"}}
    monkeypatch.setattr(LLMClient, "_post", staticmethod(fake_post))
    assert LLMClient().complete("sys", "user") == "{}"
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["payload"]["options"]["num_ctx"] == 2048
    assert seen["payload"]["options"]["num_predict"] == 1024
    assert seen["payload"]["keep_alive"] == "0"

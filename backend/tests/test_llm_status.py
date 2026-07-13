import httpx

from app.config import settings
from app.services.llm_client import OpenAICompatibleLLMClient


async def test_real_llm_failure_returns_structured_degraded_status(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "openai-compatible")
    monkeypatch.setattr(settings, "llm_api_base", "https://model.invalid/v1")

    async def fail(_messages):
        raise httpx.ConnectError("offline")

    client = OpenAICompatibleLLMClient()
    monkeypatch.setattr(client, "_chat", fail)
    result = await client.generate_answer("question", "[1] context")

    assert result.status == "error"
    assert result.mode == "degraded"
    assert result.provider == "openai-compatible"
    assert result.error_code == "llm_request_failed"
    assert "未使用 mock 回答替代" in result.content

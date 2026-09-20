"""集成测试（V 模型左中 → 集成测试，对应 REQ-102）

mock LLM，验证 FastAPI 端到端路由 + 参数校验
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from app import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /v1/health"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "openai" in data["providers"]
    assert "deepseek" in data["providers"]
    assert "MiniMax" in data["providers"]


@pytest.mark.asyncio
async def test_prompt_versions_endpoint():
    """GET /v1/prompt-versions"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/v1/prompt-versions")
    assert resp.status_code == 200
    assert "v1" in resp.json()["versions"]


@pytest.mark.asyncio
@patch("app.call_llm", new_callable=AsyncMock)
async def test_chat_with_mock_llm(mock_llm):
    """POST /v1/chat（mock LLM，验证参数传递 + provider 切换）"""
    mock_llm.return_value = "Mocked AI reply"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat", json={
            "message": "Hello",
            "provider": "MiniMax",
            "prompt_version": "v1",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Mocked AI reply"
    assert data["provider"] == "MiniMax"
    assert data["prompt_version"] == "v1"
    assert data["latency_ms"] >= 0
    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_invalid_provider():
    """REQ-001: 不支持的 provider 应该 400"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat", json={
            "message": "Hello",
            "provider": "invalid_provider",
        })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_chat_invalid_prompt_version():
    """REQ-004: 不存在的 prompt 版本应该 404"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat", json={
            "message": "Hello",
            "prompt_version": "v999",
        })
    assert resp.status_code == 404
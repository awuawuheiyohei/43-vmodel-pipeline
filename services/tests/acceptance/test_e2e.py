"""验收测试（V 模型右下 → 验收测试，对应 REQ-104）

happy path：调真实 LLM（需要 .env + 网络），验证端到端
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport

from app import app


# 跳过条件：无 LLM_API_KEY 或 CI 无网络
pytestmark = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="需要 LLM_API_KEY（验收测试只在 staging 跑）"
)


@pytest.mark.asyncio
async def test_e2e_happy_path():
    """端到端：POST /v1/chat 用真实 LLM 跑通"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat", json={
            "message": "Reply with one word: pong",
            "provider": "MiniMax",
            "prompt_version": "v2",
        }, timeout=60)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["reply"]) > 0
    assert data["provider"] == "MiniMax"
    assert data["prompt_version"] == "v2"
    # P99 阈值：单个请求 ≤ 5s（验收更宽松）
    assert data["latency_ms"] < 5000


@pytest.mark.asyncio
async def test_e2e_provider_switch():
    """REQ-001: 切换 provider 端到端"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat", json={
            "message": "Reply: ok",
            "provider": "MiniMax",
        }, timeout=60)
    assert resp.status_code == 200
    assert resp.json()["provider"] == "MiniMax"
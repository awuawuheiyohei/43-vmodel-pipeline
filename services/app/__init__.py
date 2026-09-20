"""AI/LLM Agent demo 服务（用于 V Model + CI/CD Pipeline 演示）"""

import os
from pathlib import Path
from typing import Optional, List

import yaml
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"

# LLM config
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.MiniMax.chat/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "MiniMax-M3")

# Provider config（REQ-001）
PROVIDERS = {
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "MiniMax": {"base_url": "https://api.MiniMax.chat/v1", "model": "MiniMax-M3"},
}

app = FastAPI(title="AI/LLM Agent Demo", version="0.1.0")


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = "MiniMax"  # openai / deepseek / MiniMax
    prompt_version: Optional[str] = "v1"


class ChatResponse(BaseModel):
    reply: str
    provider: str
    prompt_version: str
    latency_ms: int


# ──────────────────────────────────────────────────────────────
# Prompt 版本管理（REQ-004）
# ──────────────────────────────────────────────────────────────

def load_prompt(version: str = "v1") -> str:
    """加载 prompt YAML（version: v1/v2/...）"""
    spec_file = PROMPTS_DIR / "spec.yaml"
    if not spec_file.exists():
        raise HTTPException(500, "prompts/spec.yaml 不存在")
    data = yaml.safe_load(spec_file.read_text(encoding="utf-8"))
    version_data = data.get("versions", {}).get(version)
    if not version_data:
        raise HTTPException(404, f"prompt version {version} 不存在")
    template = version_data.get("template", "")
    return template


def list_versions() -> List[str]:
    """列所有可用 prompt 版本"""
    spec_file = PROMPTS_DIR / "spec.yaml"
    data = yaml.safe_load(spec_file.read_text(encoding="utf-8"))
    return list(data.get("versions", {}).keys())


# ──────────────────────────────────────────────────────────────
# LLM 调用（REQ-001: 3 provider 切换）
# ──────────────────────────────────────────────────────────────

async def call_llm(provider: str, message: str, prompt_template: str) -> str:
    """调 LLM（异步）"""
    if provider not in PROVIDERS:
        raise HTTPException(400, f"不支持的 provider: {provider}。支持: {list(PROVIDERS)}")
    cfg = PROVIDERS[provider]
    api_key = LLM_API_KEY or os.environ.get(f"{provider.upper()}_API_KEY", "")

    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": prompt_template},
            {"role": "user", "content": message},
        ],
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code != 200:
        raise HTTPException(502, f"LLM 调用失败 ({resp.status_code}): {resp.text[:500]}")

    return resp.json()["choices"][0]["message"]["content"]


# ──────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────

@app.get("/v1/health")
async def health():
    return {"status": "ok", "providers": list(PROVIDERS), "prompt_versions": list_versions()}


@app.get("/v1/prompt-versions")
async def prompt_versions():
    return {"versions": list_versions()}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    import time
    start = time.time()
    template = load_prompt(req.prompt_version)
    reply = await call_llm(req.provider, req.message, template)
    latency = int((time.time() - start) * 1000)
    return ChatResponse(reply=reply, provider=req.provider,
                        prompt_version=req.prompt_version, latency_ms=latency)
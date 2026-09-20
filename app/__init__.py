"""V Model Pipeline Lab core"""

import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "vmodel.db"

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.MiniMax.chat/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "MiniMax-M3")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))

# K8s in-cluster config（kubectl 默认 ~/.kube/config）
KUBECONFIG = os.environ.get("KUBECONFIG", str(Path.home() / ".kube" / "config"))


def init_db() -> sqlite3.Connection:
    """初始化 SQLite（requirements / commits / ci_runs / traceability）"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requirements (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            priority TEXT,
            v_phase TEXT NOT NULL,
            status TEXT DEFAULT 'open'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commits (
            sha TEXT PRIMARY KEY,
            message TEXT,
            req_id TEXT,
            author TEXT,
            committed_at TEXT,
            FOREIGN KEY (req_id) REFERENCES requirements(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            req_id TEXT NOT NULL,
            test_path TEXT NOT NULL,
            stage TEXT NOT NULL,  -- unit / integration / system / acceptance
            FOREIGN KEY (req_id) REFERENCES requirements(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ci_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_run TEXT UNIQUE,
            commit_sha TEXT,
            stage TEXT NOT NULL,  -- unit / integration / system / acceptance
            status TEXT NOT NULL,  -- pending / running / pass / fail / skip
            log_excerpt TEXT,
            started_at TEXT,
            finished_at TEXT,
            FOREIGN KEY (commit_sha) REFERENCES commits(sha)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_config_commits (
            sha TEXT PRIMARY KEY,
            path TEXT NOT NULL,  -- k8s/tekton-pipeline.yaml 等
            ci_self_test TEXT  -- 'pass' / 'fail'
        )
    """)
    conn.commit()
    return conn


def strip_thinking(content: str) -> str:
    """Strip LLM thinking blocks（三模式兜底）"""
    content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
    content = re.sub(r"<think>.*$", "", content, flags=re.DOTALL)
    markers = [
        r"^OK final structure:.*$",
        r"^OK let me (write|think).*$",
        r"^OK writing now.*$",
        r"^Actually[, ].*$",
        r"^Wait[, ].*$",
        r"^One more thought:.*$",
    ]
    for m in markers:
        match = re.search(m, content, flags=re.MULTILINE)
        if match:
            content = content[:match.start()].rstrip() + "\n"
            break
    return content.strip() + "\n"


def call_llm(system_prompt: str, user_prompt: str,
             api_key: str = None, base_url: str = None, model: str = None,
             temperature: float = None, max_tokens: int = 4000) -> str:
    """Call OpenAI-compatible chat completion API"""
    api_key = api_key or LLM_API_KEY
    if not api_key:
        raise ValueError("LLM_API_KEY 未配置")
    base_url = base_url or LLM_BASE_URL
    model = model or LLM_MODEL
    temperature = temperature if temperature is not None else LLM_TEMPERATURE

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "user_prompt"},
        ],
    }
    # 修：实际 message 用 user_prompt 变量
    payload["messages"][1]["content"] = user_prompt

    resp = requests.post(url, headers=headers, json=payload, timeout=300)
    if resp.status_code != 200:
        raise RuntimeError(f"LLM 调用失败 ({resp.status_code}):\n{resp.text[:1000]}")

    content = resp.json()["choices"][0]["message"]["content"]
    return strip_thinking(content)


def load_prompt(name: str) -> str:
    """Load prompt from prompts/ directory"""
    path = ROOT / "prompts" / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")
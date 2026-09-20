"""需求管理（YAML → SQLite）"""

import sqlite3
from pathlib import Path
from typing import List, Dict

import yaml

from . import init_db, ROOT


REQ_FILE = ROOT / "requirements.yaml"


def load_requirements(file_path: Path = REQ_FILE) -> List[Dict]:
    """读 requirements.yaml → list[dict]"""
    if not file_path.exists():
        return []
    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    return data.get("requirements", [])


def sync_to_db(file_path: Path = REQ_FILE) -> int:
    """同步 YAML → DB（覆盖式）"""
    reqs = load_requirements(file_path)
    conn = init_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM requirements")
    for r in reqs:
        cur.execute("""
            INSERT INTO requirements (id, text, priority, v_phase, status)
            VALUES (?, ?, ?, ?, ?)
        """, (r["id"], r["text"], r.get("priority", "medium"),
              r.get("v_phase", "system_req"), r.get("status", "open")))
    conn.commit()
    conn.close()
    return len(reqs)


def list_requirements() -> List[Dict]:
    """从 DB 读所有需求"""
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT id, text, priority, v_phase, status FROM requirements ORDER BY id")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def get_requirement(req_id: str) -> Dict | None:
    """按 ID 查需求"""
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT id, text, priority, v_phase, status FROM requirements WHERE id=?", (req_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    cols = ["id", "text", "priority", "v_phase", "status"]
    return dict(zip(cols, row))
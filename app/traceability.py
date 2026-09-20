"""需求追溯矩阵（REQ ↔ commit ↔ test ↔ CI stage）"""

import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict

from . import init_db


def parse_req_id_from_commit(message: str) -> str | None:
    """从 commit message 提取 REQ-XXX（格式: 'REQ-001: ...'）"""
    import re
    m = re.search(r"REQ-\d{3,}", message)
    return m.group(0) if m else None


def ingest_local_commits(repo_path: Path, limit: int = 50) -> int:
    """从 git log 解析 commit，存 DB（自动抓 req_id）

    Args:
        repo_path: services/ 下的 demo 服务 git 仓库
        limit: 最多处理多少条 commit
    """
    if not (repo_path / ".git").exists():
        return 0

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log", f"-n{limit}", "--pretty=format:%H|%s|%an|%ai"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    conn = init_db()
    cur = conn.cursor()
    ingested = 0
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        sha, message, author, date = line.split("|", 3)
        req_id = parse_req_id_from_commit(message)
        cur.execute("""
            INSERT OR IGNORE INTO commits (sha, message, req_id, author, committed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (sha, message, req_id, author, date))
        if cur.rowcount > 0:
            ingested += 1

    conn.commit()
    conn.close()
    return ingested


def get_traceability(req_id: str) -> Dict:
    """查 REQ-XXX 的完整追溯：commit(s) + test(s) + ci_run(s)"""
    conn = init_db()
    cur = conn.cursor()

    cur.execute("SELECT id, text, priority, v_phase, status FROM requirements WHERE id=?", (req_id,))
    req_row = cur.fetchone()
    if not req_row:
        conn.close()
        return {}
    cols = ["id", "text", "priority", "v_phase", "status"]
    req = dict(zip(cols, req_row))

    cur.execute("SELECT sha, message, author, committed_at FROM commits WHERE req_id=?", (req_id,))
    commits = [{"sha": r[0], "message": r[1], "author": r[2], "committed_at": r[3]}
               for r in cur.fetchall()]

    cur.execute("SELECT test_path, stage FROM tests WHERE req_id=?", (req_id,))
    tests = [{"test_path": r[0], "stage": r[1]} for r in cur.fetchall()]

    # CI runs via commits
    commit_shas = [c["sha"] for c in commits]
    ci_runs = []
    if commit_shas:
        placeholders = ",".join("?" * len(commit_shas))
        cur.execute(f"""
            SELECT pipeline_run, commit_sha, stage, status, log_excerpt, finished_at
            FROM ci_runs WHERE commit_sha IN ({placeholders})
            ORDER BY finished_at DESC
        """, commit_shas)
        ci_runs = [{"pipeline_run": r[0], "commit_sha": r[1], "stage": r[2],
                    "status": r[3], "log_excerpt": r[4], "finished_at": r[5]}
                   for r in cur.fetchall()]

    conn.close()
    return {
        "requirement": req,
        "commits": commits,
        "tests": tests,
        "ci_runs": ci_runs,
    }


def get_full_traceability_matrix() -> List[Dict]:
    """全量 RTM（每条 REQ 一行）"""
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM requirements ORDER BY id")
    req_ids = [r[0] for r in cur.fetchall()]
    conn.close()

    matrix = []
    for rid in req_ids:
        trace = get_traceability(rid)
        if trace:
            # 计算 stage 状态汇总
            stages = {}
            for run in trace.get("ci_runs", []):
                stage = run["stage"]
                if stage not in stages or run["status"] == "fail":
                    stages[stage] = run["status"]
            matrix.append({
                "req_id": rid,
                "text": trace["requirement"]["text"],
                "v_phase": trace["requirement"]["v_phase"],
                "commit_count": len(trace["commits"]),
                "test_count": len(trace["tests"]),
                "stages": stages,
            })
    return matrix
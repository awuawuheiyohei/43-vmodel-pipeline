"""CI 状态采集（Tekton + Argo CD status → SQLite）"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from . import init_db, KUBECONFIG


def _kubectl(args: List[str], timeout: int = 30) -> Optional[str]:
    """跑 kubectl（带 kubeconfig）"""
    try:
        result = subprocess.run(
            ["kubectl", "--kubeconfig", KUBECONFIG] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def list_pipelineruns(namespace: str = "tekton-pipelines") -> List[Dict]:
    """列 Tekton PipelineRun"""
    out = _kubectl(["get", "pipelinerun", "-n", namespace, "-o", "json"])
    if not out:
        return []
    data = json.loads(out)
    return [
        {
            "name": pr["metadata"]["name"],
            "status": pr.get("status", {}).get("conditions", [{}])[0].get("reason", "Unknown"),
            "started_at": pr.get("status", {}).get("startTime"),
            "finished_at": pr.get("status", {}).get("completionTime"),
            "commit_sha": pr.get("metadata", {}).get("labels", {}).get("tekton.dev/commit", ""),
        }
        for pr in data.get("items", [])
    ]


def list_taskruns(namespace: str = "tekton-pipelines") -> List[Dict]:
    """列 Tekton TaskRun（含每个 stage 状态）"""
    out = _kubectl(["get", "taskrun", "-n", namespace, "-o", "json"])
    if not out:
        return []
    data = json.loads(out)
    runs = []
    for tr in data.get("items", []):
        labels = tr.get("metadata", {}).get("labels", {})
        spec = tr.get("spec", {})
        runs.append({
            "name": tr["metadata"]["name"],
            "pipeline_run": labels.get("tekton.dev/pipelineRun", ""),
            "stage": labels.get("tekton.dev/task", spec.get("taskRef", {}).get("name", "unknown")),
            "status": tr.get("status", {}).get("conditions", [{}])[0].get("reason", "Unknown"),
            "started_at": tr.get("status", {}).get("startTime"),
            "finished_at": tr.get("status", {}).get("completionTime"),
        })
    return runs


def sync_to_db(namespace: str = "tekton-pipelines") -> int:
    """同步 K8s CI 状态 → SQLite"""
    pipelineruns = list_pipelineruns(namespace)
    taskruns = list_taskruns(namespace)
    if not taskruns:
        return 0

    conn = init_db()
    cur = conn.cursor()
    synced = 0
    for tr in taskruns:
        cur.execute("""
            INSERT OR REPLACE INTO ci_runs
                (pipeline_run, commit_sha, stage, status, log_excerpt, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tr["pipeline_run"],
            "",  # commit 需要从 pipelinerun 关联
            tr["stage"],
            tr["status"].lower() if tr["status"] != "Unknown" else "unknown",
            None,
            tr["started_at"],
            tr["finished_at"],
        ))
        synced += 1

    # 回填 commit_sha（从 pipelinerun → commit label）
    pr_commit = {}
    for pr in pipelineruns:
        if pr["commit_sha"]:
            pr_commit[pr["name"]] = pr["commit_sha"]

    for pr_name, commit_sha in pr_commit.items():
        cur.execute("""
            UPDATE ci_runs SET commit_sha=? WHERE pipeline_run=?
        """, (commit_sha, pr_name))

    conn.commit()
    conn.close()
    return synced


def get_stage_status(req_id: str = None) -> Dict[str, str]:
    """聚合 4 stage 状态（unit/integration/system/acceptance）"""
    conn = init_db()
    cur = conn.cursor()

    if req_id:
        cur.execute("""
            SELECT cr.stage, cr.status FROM ci_runs cr
            JOIN commits c ON cr.commit_sha = c.sha
            WHERE c.req_id = ?
            ORDER BY cr.finished_at DESC
        """, (req_id,))
    else:
        cur.execute("""
            SELECT stage, status FROM ci_runs
            ORDER BY finished_at DESC LIMIT 100
        """)

    rows = cur.fetchall()
    conn.close()

    stages = {}
    for stage, status in rows:
        # 优先 fail > pass > running > pending
        priority = {"fail": 4, "running": 3, "pass": 2, "pending": 1, "skip": 1}
        if stage not in stages or priority.get(status, 0) > priority.get(stages[stage], 0):
            stages[stage] = status
    return stages


def get_pipeline_self_test_status() -> List[Dict]:
    """meta CI：检查 pipeline YAML 是否被测过"""
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT sha, path, ci_self_test FROM pipeline_config_commits ORDER BY sha DESC")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows
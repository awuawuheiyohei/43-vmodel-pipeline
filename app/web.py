"""FastAPI Web UI（V 模型 × CI 矩阵）"""

from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse

from . import init_db
from .requirements import list_requirements, get_requirement, sync_to_db, REQ_FILE
from .traceability import get_traceability, get_full_traceability_matrix, ingest_local_commits
from .ci_status import (
    sync_to_db as sync_ci_db,
    get_stage_status,
    get_pipeline_self_test_status,
)
from .v_explainer import explain_ci_failure, explain_all_failures

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="V Model Pipeline Lab", version="0.1")


@app.on_event("startup")
def _startup():
    """启动时同步 requirements + 初始化 DB"""
    init_db()
    sync_to_db()


@app.get("/", response_class=HTMLResponse)
async def index():
    """首页：V Model × CI 矩阵"""
    index_html = WEB_DIR / "index.html"
    if not index_html.exists():
        return HTMLResponse("<h1>V Model Pipeline Lab</h1><p>Web UI 未构建。</p>")
    return FileResponse(index_html)


@app.get("/api/traceability")
async def api_traceability():
    """完整 RTM（V Model × CI 矩阵）"""
    matrix = get_full_traceability_matrix()
    return {"count": len(matrix), "matrix": matrix}


@app.get("/api/traceability/{req_id}")
async def api_trace_one(req_id: str):
    """单条 REQ 的完整追溯"""
    trace = get_traceability(req_id)
    return trace or {"error": f"REQ not found: {req_id}"}


@app.get("/api/requirements")
async def api_requirements():
    """所有需求"""
    reqs = list_requirements()
    return {"count": len(reqs), "requirements": reqs}


@app.get("/api/ci/sync")
async def api_ci_sync():
    """手动触发同步 Tekton 状态"""
    n = sync_ci_db()
    return {"synced": n}


@app.get("//api/ci/status")
async def api_ci_status():
    """当前 stage 聚合状态"""
    return {"stages": get_stage_status()}


@app.get("/api/ci/explain")
async def api_ci_explain(stage: str, status: str, log: str = "", req_id: str = None):
    """LLM 解读单条 CI 状态"""
    md = explain_ci_failure(stage, status, log, req_id)
    return {"markdown": md}


@app.get("/api/ci/explain-all")
async def api_ci_explain_all():
    """LLM 批量解读所有失败"""
    return {"markdown": explain_all_failures()}


@app.get("/api/meta-ci")
async def api_meta_ci():
    """meta CI 状态（pipeline 配置本身的测试）"""
    return {"configs": get_pipeline_self_test_status()}


@app.get("/api/commits/sync")
async def api_commits_sync(repo: str = Query("../services", description="demo 服务路径")):
    """从 demo 服务的 git log 同步 commits"""
    repo_path = Path(repo).resolve()
    n = ingest_local_commits(repo_path)
    return {"ingested": n}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003, log_level="info")


if __name__ == "__main__":
    main()
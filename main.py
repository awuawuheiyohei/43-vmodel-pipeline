"""CLI 入口: serve / sync / trace / explain"""

import argparse
import sys


def cmd_serve(args):
    """启动 Web"""
    from app.web import main as serve_main
    serve_main()


def cmd_sync_req(args):
    """同步 requirements.yaml → DB"""
    from app.requirements import sync_to_db
    n = sync_to_db()
    print(f"✅ 已同步 {n} 条需求到 DB")


def cmd_sync_ci(args):
    """同步 Tekton status → DB"""
    from app.ci_status import sync_to_db
    n = sync_to_db()
    print(f"✅ 已同步 {n} 条 CI run")


def cmd_sync_commits(args):
    """从 git log 同步 commits → DB"""
    from pathlib import Path
    from app.traceability import ingest_local_commits
    repo = Path(args.repo).resolve()
    n = ingest_local_commits(repo)
    print(f"✅ 已 ingest {n} 条 commit (repo: {repo})")


def cmd_trace(args):
    """查 RTM（单条 REQ 或全量）"""
    from app.traceability import get_traceability, get_full_traceability_matrix

    if args.req_id:
        t = get_traceability(args.req_id)
        if not t:
            print(f"❌ REQ {args.req_id} 不存在")
            return
        print(f"## {t['requirement']['id']}: {t['requirement']['text']}")
        print(f"V 阶段: {t['requirement']['v_phase']} | 优先级: {t['requirement']['priority']}")
        print(f"\n### Commits ({len(t['commits'])})")
        for c in t['commits']:
            print(f"- `{c['sha'][:8]}` {c['message'][:60]} ({c['author']})")
        print(f"\n### Tests ({len(t['tests'])})")
        for tt in t['tests']:
            print(f"- [{tt['stage']}] {tt['test_path']}")
        print(f"\n### CI Runs ({len(t['ci_runs'])})")
        for r in t['ci_runs']:
            print(f"- [{r['status']}] {r['stage']} | {r['pipeline_run']}")
    else:
        m = get_full_traceability_matrix()
        if not m:
            print("❌ RTM 为空。先跑 `python main.py sync-req`")
            return
        print(f"# 完整 RTM（{len(m)} 条 REQ）\n")
        print("| REQ | V 阶段 | commits | tests | stages |")
        print("|---|---|---|---|---|")
        for r in m:
            stages_str = ", ".join(f"{s}={st}" for s, st in r['stages'].items())
            print(f"| {r['req_id']} | {r['v_phase']} | {r['commit_count']} | {r['test_count']} | {stages_str or '无'} |")


def cmd_explain(args):
    """LLM 解读 CI 失败"""
    from app.v_explainer import explain_ci_failure
    if args.all:
        from app.v_explainer import explain_all_failures
        print(explain_all_failures())
    else:
        md = explain_ci_failure(args.stage, "fail", args.log, args.req_id)
        print(md)


def main():
    parser = argparse.ArgumentParser(description="V Model Pipeline Lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("serve", help="启动 Web UI（端口 5003）")

    p = sub.add_parser("sync-req", help="同步 requirements.yaml → DB")
    p = sub.add_parser("sync-ci", help="同步 Tekton status → DB")

    p = sub.add_parser("sync-commits", help="从 git log 同步 commits")
    p.add_argument("--repo", default="../services", help="demo 服务 git 仓库路径")

    p = sub.add_parser("trace", help="查 RTM")
    p.add_argument("req_id", nargs="?", help="REQ-XXX（不填则全量）")

    p = sub.add_parser("explain", help="LLM 解读 CI 失败")
    p.add_argument("--stage", choices=["unit", "integration", "system", "acceptance"],
                   default="integration")
    p.add_argument("--log", default="", help="错误日志")
    p.add_argument("--req-id", help="关联 REQ")
    p.add_argument("--all", action="store_true", help="批量解读所有失败")

    args = parser.parse_args()
    dispatch = {
        "serve": cmd_serve,
        "sync-req": cmd_sync_req,
        "sync-ci": cmd_sync_ci,
        "sync-commits": cmd_sync_commits,
        "trace": cmd_trace,
        "explain": cmd_explain,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
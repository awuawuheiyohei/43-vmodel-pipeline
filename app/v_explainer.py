"""LLM 解读 CI 失败 → V 模型阶段 + 修复建议"""

import json
from typing import Dict

from . import call_llm, load_prompt


def explain_ci_failure(stage: str, status: str, log_excerpt: str,
                       req_id: str = None) -> str:
    """LLM 解读 CI 失败（输出含 V 模型阶段 + 修复建议）

    Args:
        stage: unit / integration / system / acceptance
        status: fail / pending / running / pass
        log_excerpt: CI 错误日志截取
        req_id: 关联的需求 ID（可选）

    Returns:
        markdown 格式解读（含 "对应 V 模型阶段" + 源 log + 修复建议）
    """
    if status != "fail":
        return f"✅ Stage `{stage}` 当前状态: {status}（无需解读）\n"

    system = load_prompt("v_explainer.md")

    v_phase_map = {
        "unit": "V 模型左下 → 单元测试（对应右上的验收验证）",
        "integration": "V 模型左中 → 集成测试（对应右中的系统验证）",
        "system": "V 模型右下 → 系统测试",
        "acceptance": "V 模型右下 → 验收测试（用户场景）",
    }
    v_phase = v_phase_map.get(stage, "未知 V 模型阶段")

    user = f"""CI 失败信息：

- **Stage**: `{stage}`（对应 V 模型阶段: {v_phase}）
- **状态**: {status}
- **关联 REQ**: {req_id or '（未指定）'}
- **日志截取**:
```
{log_excerpt[:2000] if log_excerpt else '（无日志）'}
```

请输出 markdown 格式解读，包含：
1. **对应 V 模型阶段**: {v_phase}
2. **失败原因**（基于日志，不臆测）
3. **修复建议**（具体到代码/配置层面）
4. **是否需要回退到上一阶段**（如 unit 失败 → 回到实现阶段）

约束：
- 不编造日志里没有的信息
- 建议要可执行（如"修改 X 文件的 Y 函数"），不要泛泛而谈
"""

    return call_llm(system, user, temperature=0.3, max_tokens=1500)


def explain_all_failures() -> str:
    """批量解读当前所有失败的 CI run"""
    from . import init_db
    conn = init_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT pipeline_run, stage, log_excerpt
        FROM ci_runs WHERE status='fail'
        ORDER BY finished_at DESC LIMIT 10
    """)
    fails = cur.fetchall()
    conn.close()

    if not fails:
        return "✅ 当前无 CI 失败\n"

    out = ["# 🔍 CI 失败 AI 解读（V 模型定位）\n"]
    for pr_name, stage, log in fails:
        out.append(f"\n## PipelineRun: `{pr_name}`\n")
        out.append(explain_ci_failure(stage, "fail", log))

    return "\n".join(out)
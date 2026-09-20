# V Model + CI/CD Pipeline Lab — PRD

> **一句话**：本地 k3d + Argo CD + Tekton 跑 AI/LLM 服务的完整 V 模型开发流水线，每个 commit 都可追溯到 System Requirements。
> 配套 **Web UI 实时显示 V 模型阶段 ↔ CI stage 状态** —— 面试能 demo 的"具体场景"。

---

## 🎯 用户

我自己——多次头部企业面试被问 V 模型 + CI/CD，需要**真实能跑**的演示项目，不是 PPT。

**目标 JD 类型**：
- 嵌入式/安全关键（EN 50126/ISO 26262）→ V 模型是必问
- DevOps/SRE 岗位 → CI/CD 流水线 + GitOps 是核心
- AI/LLM 工程化 → prompt spec 视为"需求"，对应 V 模型思维

---

## 📥 输入

### 1. 需求（System Requirements）

```yaml
service: ai-llm-agent
requirements:
  - id: REQ-001
    text: "支持 3 种 LLM（OpenAI / DeepSeek / MiniMax）切换"
    priority: high
    v_phase: system_req
  - id: REQ-002
    text: "QPS ≥ 10（单实例）"
    priority: medium
    v_phase: system_req
  - id: REQ-003
    text: "P99 延迟 ≤ 2s"
    priority: medium
    v_phase: system_req
  - id: REQ-004
    text: "支持 prompt 模板版本管理"
    priority: high
    v_phase: system_req
```

### 2. CI 触发

```bash
git push origin main  # 或 PR merge
# → Tekton PipelineRun 自动跑
# → 4 stage: unit / integration / system / acceptance
# → 每个 stage 标 V 模型阶段
```

---

## 📤 输出

### 1. Web UI（实时 V 模型 × CI 矩阵）

```markdown
# V Model × CI/CD 实时状态

## System Requirements（5 条）
- REQ-001: ✅ 单元测试通过 → REQ-002: ✅ ... 

## Architecture Design
- 架构图: [mermaid]
- 决策记录: ADR-001 (OpenAI 兼容接口)

## ↓ 实现 ↓
## CI Stage 1: 单元测试（对应 V 模型单元测试）
  [PASS] test_prompt_template.py::test_version
  [PASS] test_llm_client.py::test_openai_compat
  [FAIL] test_llm_client.py::test_timeout

## CI Stage 2: 集成测试（对应 V 模型集成测试）
  [RUNNING] docker compose up -d postgres redis
  [PENDING] test_integration.py

## CI Stage 3: 系统测试（对应 V 模型系统测试）
  [SKIP] k6 load test (需要 staging)

## CI Stage 4: 验收测试（对应 V 模型验收测试）
  [PASS] smoke test against deployed service
```

### 2. 需求追溯矩阵（Requirements Traceability Matrix）

```python
REQ-001 → ARCH-001 → IMP-prompt_router.py → TEST-test_prompt.py → CI stage 1 (PASS)
REQ-002 → ARCH-002 → IMP-rate_limiter.py  → TEST-test_rate.py   → CI stage 2 (PENDING)
```

### 3. AI 解读（CI 失败时）

```
"Stage 2 集成测试失败，对应 V 模型的【集成测试】阶段。
失败原因：postgres 连接超时（>5s）
建议：检查 docker compose 网络配置 + Postgres healthcheck"
```

---

## 🏗 架构（v1.0 MVP）

```
vmodel-pipeline/
├── README.md
├── PRD.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── app/
│   ├── __init__.py        # init_db + call_llm + strip_thinking
│   ├── main.py            # CLI: serve / status / trace / ai-explain
│   ├── requirements.py    # REQ-* 加载（YAML）
│   ├── traceability.py    # req_id ↔ commit ↔ test_case 映射
│   ├── ci_status.py       # 监听 Tekton / Argo CD status
│   ├── v_explainer.py     # LLM 解读 CI 失败（V 模型阶段）
│   └── web.py             # FastAPI Web UI
├── prompts/
│   ├── v_explainer.md
│   └── traceability.md
├── k8s/                    # Tekton / Argo CD 配置
│   ├── tekton-pipeline.yaml
│   ├── tekton-pipelinerun.yaml
│   ├── argocd-application.yaml
│   └── kustomization.yaml
├── services/                # demo 服务（AI/LLM Agent）
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/main.py          # FastAPI
│   ├── prompts/spec.yaml    # prompt 版本管理
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── acceptance/
├── web/                     # V Model × CI Web UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   └── vmodel.db           # SQLite（req_id 追溯 + CI 状态）
└── tests/
```

### 技术选型

- **本地 K8s**：k3d（macOS Docker Desktop 友好，无需 VM）
- **CI/CD**：Tekton（pipeline CRD，原生 K8s）+ Argo CD（GitOps 部署）
- **demo 服务**：FastAPI + LLM Agent + PostgreSQL + Redis
- **Web UI**：FastAPI + vanilla JS（V Model 矩阵可视化）
- **LLM**：MiniMax-M3（沿用其他 3 个项目 .env）
- **SQLite**：本地追溯矩阵 + CI 状态存档

### 数据流

```
需求 (requirements.yaml)
  ↓
代码 commit (req_id 字段)
  ↓
git push → Tekton PipelineRun 触发
  ↓
4 stage CI (lint/unit/integration/acceptance)
  ↓
状态 → SQLite + Argo CD 部署 staging
  ↓
Web UI 显示 V 模型 × CI 矩阵
  ↓
CI 失败 → LLM 解读 V 模型阶段 + 修复建议
```

---

## 🚫 反模式

- **🚨 禁止"PPT 流水线"**：必须真实能跑 `kubectl get pods` 看到 Tekton / Argo CD 起来
- **🚨 禁止"假 V 模型"**：每个 commit 必须含 `req_id:` 字段，否则 CI 失败
- **🚨 禁止"黑盒 CI"**：CI 配置本身要被测（"meta CI" —— pipeline 配置错，pipeline 自己就 fail）
- **🚨 禁止"魔法需求"**：REQ-* 必须可追溯到代码 + 测试 + CI stage
- **🚨 禁止 hallucination 解读**：LLM 解读必须含 "对应 V 模型阶段" + "源数据"（具体 log / test 输出）
- **🚨 禁止"云服务依赖"**：本地 k3d 跑通，不依赖 AWS/Azure/GCP

---

## 🎯 v1.0 验收标准（4-8 周）

- [ ] `k3d cluster create` 起本地 K8s 集群
- [ ] `kubectl apply` 部署 Tekton + Argo CD
- [ ] `python main.py serve` 启动 Web UI（端口 5003）
- [ ] 提交 1 个含 req_id 的 commit → Tekton 自动跑 4 stage
- [ ] Web UI 显示 V 模型 × CI 矩阵实时状态
- [ ] CI 失败时 LLM 解读 V 模型阶段 + 修复建议
- [ ] Requirements Traceability Matrix 完整（req ↔ commit ↔ test ↔ stage）
- [ ] 真实跑 1 周无 bug

---

## 🚀 v1.1

- Argo Rollouts 做蓝绿发布（金丝雀）
- Tekton Chains 做供应链签名（SLSA）
- 集成钉钉（CI 状态推送）
- 集成 Grafana（V 模型指标 dashboard）

---

## 🚀 v1.2

- 对接真实 LLM 服务（mother-care / career-coach）的 CI/CD
- 多租户（多个服务共用 pipeline）

---

## 📝 与已有项目的关系

- **.env 复用**：沿用 `Interview/.env`（LLM key + base URL）
- **`_strip_thinking` 复用**：app/__init__.py 直接 copy `rss-reader/app/__init__.py` 的实现
- **`call_llm` 复用**：相同 OpenAI 兼容协议
- **Dashboard 集成**：未来在 Interview/projects-portfolio.md 加 "12. V Model + CI/CD Pipeline Lab ⭐⭐⭐⭐⭐"

---

## 💡 面试讲法（预设）

1. "**完整 V 模型闭环**：需求 → 设计 → 实现 → 测试，每步可追溯"
2. "**本地 K8s 自托管**：k3d + Tekton + Argo CD，无云依赖"
3. "**CI 配置也是被测对象**：meta CI 思路，pipeline 自身 bug 也能被 CI 抓到"
4. "**LLM 解读 CI 失败**：把'看 log 自己 debug'变成'V 模型阶段定位'"
5. "**Requirements Traceability Matrix**：面试官问 RTM 时直接展示"
6. "**真实 AI/LLM 服务 demo**：V 模型不是 PPT，是真的在跑 LLM Agent 的 CI/CD"

---

**v0.1 PRD — 2026-09-20 起算**
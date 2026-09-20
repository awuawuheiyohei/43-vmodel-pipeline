# V Model + CI/CD Pipeline Lab

> 本地 k3d + Tekton + Argo CD 跑 AI/LLM 服务的完整 V 模型开发流水线，每个 commit 都可追溯到 System Requirements。
> **当前状态**：v0.1 PRD + 代码骨架完成（2026-09-20）。v1.0 真实跑通需要本地 K8s 环境（k3d + Docker daemon）。

---

## ✨ 核心特性

- **V 模型双向追溯**：每条 REQ-* 必须有对应 commit + test + 4 stage CI run
- **meta CI**：Tekton pipeline 配置本身也是被测对象（pipeline 错 → pipeline fail）
- **Web UI 实时矩阵**：4 tab（V×CI 矩阵 / 追溯详情 / meta CI / AI 解读）
- **LLM 解读 CI 失败**：定位 V 模型阶段 + 修复建议
- **本地自托管**：k3d + Docker Desktop/colima，无云依赖
- **零订阅费**：开源工具链（Tekton + Argo CD + k3d）

---

## 🚀 快速开始

### 1. K8s 环境（一次性）

```bash
# 安装 Docker runtime
brew install colima
colima start

# 安装 k3d + helm + kubectl
brew install k3d helm

# 起本地集群
k3d cluster create vmodel

# 装 Tekton
kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml

# 装 Argo CD
kubectl create namespace argocd
kubectl apply -n argocd --filename https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 2. 应用 Pipeline 配置

```bash
cd /Users/jiangwenrui/Downloads/mass/vmodel-pipeline

# 命名空间 + Tekton tasks + Pipeline + Argo CD
kubectl apply -k k8s/

# 验证
kubectl get pipelinerun -n vmodel-pipeline
kubectl get application -n argocd
```

### 3. 启动 V Model Lab Web UI

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env  # 编辑填 LLM_API_KEY

# 同步 requirements 到 DB
python main.py sync-req

# 启动 Web UI（端口 5003）
python main.py serve
# 访问 http://localhost:5003
```

### 4. CLI 使用

```bash
# 同步 requirements → DB
python main.py sync-req

# 从 services/ 仓库同步 commits
python main.py sync-commits --repo ./services

# 同步 Tekton CI 状态 → DB
python main.py sync-ci

# 查 RTM（全量）
python main.py trace

# 查单条 REQ 追溯
python main.py trace REQ-001

# LLM 解读 CI 失败
python main.py explain --stage integration --log "Connection refused" --req-id REQ-102

# 批量解读所有失败
python main.py explain --all
```

---

## 📁 项目结构

```
vmodel-pipeline/
├── README.md
├── PRD.md
├── requirements.yaml          # 11 条 REQ（系统/测试/meta CI 三层）
├── pyproject.toml
├── .env.example
├── main.py                    # CLI: serve / sync / trace / explain
├── app/
│   ├── __init__.py            # init_db + call_llm + strip_thinking
│   ├── requirements.py        # requirements.yaml ↔ SQLite
│   ├── traceability.py        # REQ ↔ commit ↔ test ↔ CI run
│   ├── ci_status.py           # Tekton/Argo CD status 采集
│   ├── v_explainer.py         # V 模型阶段 LLM 解读
│   └── web.py                 # FastAPI（端口 5003）
├── prompts/
│   ├── v_explainer.md         # 解读 prompt
│   └── traceability.md        # RTM 评估 prompt
├── k8s/
│   ├── tekton-tasks.yaml      # 5 个 Task（unit/integration/system/acceptance/meta-ci）
│   ├── tekton-pipeline.yaml   # Pipeline + PipelineRun（4 stage + meta CI）
│   ├── argocd-application.yaml # GitOps 部署 demo 服务
│   └── kustomization.yaml     # 一键 apply
├── services/                  # AI/LLM Agent demo 服务
│   ├── Dockerfile
│   ├── docker-compose.yml     # postgres + redis（集成测试）
│   ├── pyproject.toml
│   ├── app/__init__.py        # FastAPI: /v1/health /v1/chat
│   ├── prompts/spec.yaml      # prompt 版本管理（v1/v2）
│   ├── tests/
│   │   ├── unit/             # 单元测试（V 模型左下）
│   │   ├── integration/      # 集成测试（V 模型左中，mock LLM）
│   │   ├── system/           # 系统测试（k6 负载脚本验证）
│   │   └── acceptance/       # 验收测试（真实 LLM，需 env）
│   └── k8s/deployment.yaml   # demo 服务 Deployment
```

---

## 🎯 V 模型对应表

| V 模型阶段（左 ↘） | 本项目体现 | REQ 范围 |
|---|---|---|
| 系统需求（System Requirements） | `requirements.yaml` 11 条 REQ | REQ-001~005 |
| 架构设计（System Design） | services/ 代码结构 + FastAPI 路由 | REQ-001~005 |
| 子系统设计（Subsystem Design） | services/app/__init__.py 函数划分 | REQ-001~005 |
| 实现（Implementation） | `git commit` + 强制 `req_id:` 字段 | REQ-001~005 |
| **单元测试** | `tests/unit/` | REQ-101 |
| **集成测试** | `tests/integration/` + docker-compose | REQ-102 |
| **系统测试** | `tests/system/` + k6 脚本 | REQ-103 |
| **验收测试** | `tests/acceptance/` + 真实 LLM | REQ-104 |
| **meta CI** | Tekton pipeline 自检 task | REQ-201~202 |

---

## 🚫 反模式（PRD §反模式）

- ❌ PPT 流水线（必须 `kubectl get pods` 看到 Tekton / Argo CD 起来）
- ❌ 假 V 模型（REQ-* 必须可追溯到代码 + 测试 + CI stage）
- ❌ 黑盒 CI（pipeline 配置要进 git，被测、被 review）
- ❌ Hallucination 解读（LLM 必须含 "对应 V 模型阶段" + 源 log）
- ❌ 云服务依赖（本地 k3d 跑通）

---

## 🔒 隐私与安全

- ✅ 数据全部本地（SQLite `data/vmodel.db`）
- ✅ k3d 集群只跑本地（不暴露 6443 端口给公网）
- ✅ Argo CD 默认关闭 webhook（本地 cluster 只手动 sync）
- ✅ LLM 调用只发 CI log + REQ ID（不发送 commit 作者、邮箱）
- ✅ `.env` 已 gitignore

---

## 🎯 v1.0 验收标准（待 K8s 环境就绪后验证）

- [ ] `k3d cluster create vmodel` 起本地 K8s 集群
- [ ] `kubectl apply -k k8s/` 部署 Tekton + Argo CD
- [ ] `python main.py serve` 启动 Web UI（端口 5003）
- [ ] 提交 1 个含 req_id 的 commit → Tekton 自动跑 4 stage
- [ ] Web UI 显示 V 模型 × CI 矩阵实时状态
- [x] **CI 失败时 LLM 解读 V 模型阶段**（2026-09-20 端到端跑通，637 字符输出含 V 阶段 + log 引用 + 4 条具体修复 + 回退判断）
- [ ] Requirements Traceability Matrix 完整
- [ ] **真实跑 1 周无 bug**

---

## 🚀 Roadmap

### v1.0（MVP）
- K8s + Tekton + Argo CD + LLM 解读全部跑通

### v1.1
- Argo Rollouts 蓝绿发布（金丝雀）
- Tekton Chains 供应链签名（SLSA L3）
- 集成钉钉（CI 状态推送）
- 集成 Grafana（V 模型指标 dashboard）

### v1.2
- 对接真实 LLM 服务（mother-care / career-coach）的 CI/CD
- 多租户（多个服务共用 pipeline）

---

## 📝 开发笔记

- 与已有 3 个项目共享：`.env`（LLM key）+ `_strip_thinking` 三模式兜底
- Tekton Task 都用 `$(params.repo-url)` 注入 demo 服务仓库（避免硬编码）
- meta CI 先于 unit-test 跑（pipeline 配置错 → 整条 pipeline fail）
- Web UI 用 vanilla JS（无 React/Vue 依赖），端口 5003（错开 rss-reader 5002）

---

**v0.1 — 2026-09-20 PRD + 骨架完成**
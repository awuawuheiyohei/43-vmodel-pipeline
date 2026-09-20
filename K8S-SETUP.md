# K8S 环境搭建检查清单（macOS）

> 适用：macOS（Apple Silicon M1/M2/M4）+ Docker Desktop / colima
> 目标：本地 k3d 集群 + Tekton + Argo CD，跑 `vmodel-pipeline/k8s/`
> **写于 2026-09-20**，复盘 macOS K8s 各种坑。

---

## 🚨 第一步：检查现状（30 秒）

```bash
# 1.brew
brew --version          # 应 ≥ 4.0

# 2. Xcode license（**最容易卡**）
xcodebuild -license 2>&1 | head -3
# 如果看到 "You have not agreed"，跑下一步

# 3. Docker runtime
docker --version        # 应有
docker ps 2>&1 | head -3
# 如果 "Cannot connect to the Docker daemon"，需要起 runtime

# 4. kubectl（应已有）
kubectl version --client

# 5. K8s 相关工具
for cmd in k3d helm; do
  command -v $cmd && echo "✅ $cmd: 已装" || echo "❌ $cmd: 未装"
done
```

---

## 🛠 第二步：装 Docker runtime（必须先做）

### 方案 A：colima（推荐，零 Docker Desktop 依赖）

```bash
# ⚠️ 需要 sudo 密码（一次性）
sudo xcodebuild -license accept
brew install colima
colima start
# 等 ~3 分钟，图标变绿
docker ps  # 应有输出（不是 error）
```

**资源建议**：`colima start --cpu 4 --memory 8 --disk 50`

### 方案 B：Docker Desktop.app

```bash
# 1. 启动 Docker Desktop.app（手动）
open -a Docker

# 2. 等 daemon 起来（图标变绿，~30 秒 - 2 分钟）
docker ps
```

### 方案 C：OrbStack（最轻量，但收费）

```bash
brew install orbstack
# 启动 OrbStack.app，运行时自动开
```

---

## 📦 第三步：装 K8s 工具

```bash
# k3d + helm
brew install k3d helm

# 验证
k3d version
helm version
```

---

## 🎯 第四步：起本地集群

```bash
# 创建集群（默认 1 server + 2 agent）
k3d cluster create vmodel

# 验证
kubectl get nodes
# 应输出：
# NAME                STATUS   ROLES                  AGE   VERSION
# k3d-vmodel-server-0  Ready    control-plane,master   30s   v1.31.x
# k3d-vmodel-agent-0   Ready    <none>                 20s   v1.31.x
# k3d-vmodel-agent-1   Ready    <none>                 20s   v1.31.x

# 看集群信息
k3d cluster list
kubectl cluster-info
```

**注意**：集群名 `vmodel` 决定了 `kubectl get pods -A` 看到的命名空间前缀是 `k3d-vmodel-*`。

---

## 🔧 第五步：装 Tekton

```bash
# 最新稳定版（v0.62+）
kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml

# 验证（~30 秒等 pods Ready）
kubectl get pods -n tekton-pipelines
# 应输出：
# NAME                              READY   STATUS    RESTARTS   AGE
# tekton-pipelines-controller       1/1     Running   0          30s
# tekton-pipelines-webhook          1/1     Running   0          30s
# tekton-pipelines-taskruns         1/1     Running   0          30s
# tekton-pipelines-pipelineruns     1/1     Running   0          30s
```

**若想 dashboard**（UI 看 PipelineRun）：
```bash
kubectl apply -f https://github.com/tektoncd/dashboard/releases/latest/download/tekton-dashboard-release.yaml
kubectl port-forward -n tekton-pipelines svc/tekton-dashboard 9097:9097
# 浏览器打开 http://localhost:9097
```

---

## 🚢 第六步：装 Argo CD

```bash
# 创建 namespace
kubectl create namespace argocd

# 装 Argo CD（稳定版）
kubectl apply -n argocd --filename https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 验证（~1 分钟等 pods Ready）
kubectl get pods -n argocd
# 应输出：application-controller / dex-server / redis / repo-server / server 都 Running
```

**暴露 Argo CD UI**：
```bash
# port-forward（开发用）
kubectl port-forward svc/argocd-server -n argocd 8080:443
# 浏览器 https://localhost:8080

# 默认账号: admin
# 初始密码（自动生成）:
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

---

## 🚀 第七步：部署 vmodel-pipeline

```bash
cd /Users/jiangwenrui/Downloads/mass/vmodel-pipeline

# 1. 创建项目 namespace
kubectl create namespace vmodel-pipeline
kubectl create namespace vmodel-staging

# 2. 应用 Tekton + Argo CD 配置（一键）
kubectl apply -k k8s/

# 3. 验证
kubectl get tasks -n vmodel-pipeline
# 应输出：meta-ci / unit-test / integration-test / system-test / acceptance-test

kubectl get pipeline -n vmodel-pipeline
# 应输出：vmodel-pipeline

kubectl get application -n argocd
# 应输出：ai-llm-agent
```

---

## 🧪 第八步：触发 PipelineRun 验证

### 1. 创建 demo 服务 git 仓库（一次性）

```bash
# 把 services/ 子目录初始化成 git 仓库
cd /Users/jiangwenrui/Downloads/mass/vmodel-pipeline/services
git init
git add .
git commit -m "REQ-001,REQ-004,REQ-005: initial AI/LLM Agent demo"

# ⚠️ 改成你自己的 GitHub 仓库 URL（pipeline 拉取用）
# 推到 GitHub（公开仓库便于 Tekton 拉取）
git remote add origin https://github.com/awuawuheiyohei/vmodel-demo-service.git
git push -u origin main
```

### 2. 改 Tekton PipelineRun 用你的 repo URL

```bash
cd /Users/jiangwenrui/Downloads/mass/vmodel-pipeline
# 编辑 k8s/tekton-pipeline.yaml 里 PipelineRun 的 repo-url 参数
sed -i '' 's|https://github.com/awuawuheiyohei/vmodel-demo-service.git|YOUR_REPO_URL|' k8s/tekton-pipeline.yaml
kubectl apply -f k8s/tekton-pipeline.yaml
```

### 3. 触发第一次 PipelineRun

```bash
# 手动创建 PipelineRun
kubectl create -f k8s/tekton-pipeline.yaml

# 看状态
kubectl get pipelinerun -n vmodel-pipeline
kubectl describe pipelinerun -n vmodel-pipeline vmodel-pipelinerun-sample

# 看 log（如果某 stage 失败）
kubectl logs -n vmodel-pipeline -l tekton.dev/taskRun=<taskrun-name>
```

---

## 🌐 第九步：起 vmodel-pipeline Web UI

```bash
cd /Users/jiangwenrui/Downloads/mass/vmodel-pipeline
source .venv/bin/activate

# 同步 K8s CI 状态 → SQLite
python main.py sync-ci

# 同步 requirements → SQLite
python main.py sync-req

# 启动 Web UI（端口 5003）
python main.py serve

# 浏览器: http://localhost:5003
```

---

## 🔥 常见坑（macOS + k3d）

### 1. **Docker daemon 起不来**

症状：
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```
修法：colima 没起 / Docker Desktop.app 没运行。  
检查：`docker ps` + `colima status` 或看 Docker Desktop 图标颜色。

### 2. **k3d cluster 创建后 kubectl 看不到节点**

症状：`kubectl get nodes` 空 / k3d cluster list 显示 cluster 但 kubectl 报 connection refused。

修法：
```bash
# k3d 自动写 kubeconfig，但有时错过
export KUBECONFIG="$(k3d kubeconfig get vmodel)"
# 或合并到 ~/.kube/config
k3d kubeconfig get vmodel > ~/.kube/config
kubectl get nodes
```

### 3. **Tekton pods ImagePullBackOff**

症状：Tekton pods 起不来，状态 `ImagePullBackOff` / `ErrImagePull`。

修法：网络问题（GFW 拦截 gcr.io / docker.io）。  
备选：用国内镜像
```bash
# k3d 创建时加 registry mirror
k3d cluster create vmodel --registry-config <(echo 'mirrors:
  "docker.io":
    - "https://docker.m.daocloud.io"
  "gcr.io":
    - "https://gcr.m.daocloud.io"
  "ghcr.io":
    - "https://ghcr.m.daocloud.io"')
```

### 4. **Argo CD 应用 `OutOfSync` 但 sync 不动**

症状：`kubectl get application -n argocd` 显示 `OutOfSync`，`argocd app sync` 报 `permission denied`。

修法：AppProject 没授权 → 改 `k8s/argocd-application.yaml` 里的 destinations。

### 5. **k3d cluster 占资源太大**

症状：风扇狂转 / 系统卡。

修法：
```bash
# 看 CPU/内存
colima status
# 调整
colima stop
colima start --cpu 2 --memory 4
```

### 6. **Tekton 拉私有 GitHub 仓库失败**

症状：PipelineRun 停在 `checkout` step，`Error: authentication required`。

修法：需要 GitHub token secret，详见 [`github.com/tektoncd/pipeline/blob/main/docs/auth.md`](https://github.com/tektoncd/pipeline/blob/main/docs/auth.md)。

---

## 🧹 第十步：清理

```bash
# 删集群（释放资源）
k3d cluster delete vmodel

# 关 colima
colima stop

# 彻底删
colima delete
```

---

## 📋 检查清单

- [ ] `xcodebuild -license` accepted
- [ ] Docker daemon running（`docker ps` 通）
- [ ] `k3d` / `helm` 已装
- [ ] `k3d cluster create vmodel` 成功
- [ ] `kubectl get nodes` 看到 3 个 Ready
- [ ] Tekton 5 pods Running
- [ ] Argo CD pods Running
- [ ] `kubectl apply -k k8s/` 应用成功
- [ ] demo 服务 git 仓库创建 + push
- [ ] PipelineRun 触发成功
- [ ] Web UI 启动 + V×CI 矩阵显示

---

## 🆘 救命命令

```bash
# 看所有 namespace 的所有 pod
kubectl get pods -A

# 看具体 pod 的 log
kubectl logs -n <ns> <pod-name>

# 进 pod 内部 debug
kubectl exec -it -n <ns> <pod-name> -- /bin/sh

# 看 K8s 事件
kubectl get events -n <ns> --sort-by='.lastTimestamp'

# 重置 k3d
k3d cluster delete vmodel
k3d cluster create vmodel

# 完全重置（删 colima VM）
colima delete && colima start
```

---

## 🔗 相关链接

- k3d 文档：https://k3d.io/
- Tekton 文档：https://tekton.dev/docs/
- Argo CD 文档：https://argo-cd.readthedocs.io/
- macOS K8s 调试：https://github.com/kubernetes-sigs/kind/issues/1500

---

**写于 2026-09-20 · Mavis v0.1**
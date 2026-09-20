// V Model Pipeline Lab 前端（vanilla JS，零依赖）

const API = "";

document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById(tab.dataset.tab).classList.add("active");

        if (tab.dataset.tab === "matrix" && !document.getElementById("matrix-content").dataset.loaded) {
            loadMatrix();
        } else if (tab.dataset.tab === "meta") {
            loadMetaCI();
        }
    });
});

// 矩阵
document.getElementById("refresh-matrix").addEventListener("click", loadMatrix);

async function loadMatrix() {
    const el = document.getElementById("matrix-content");
    el.innerHTML = "🔄 加载中...";
    try {
        const resp = await fetch(`${API}/api/traceability`);
        const data = await resp.json();
        if (data.count === 0) {
            el.innerHTML = `<p style="color: #757575;">暂无需求。先跑：<code>python main.py sync-req</code></p>`;
            el.dataset.loaded = "1";
            return;
        }
        el.innerHTML = renderMatrix(data.matrix);
        el.dataset.loaded = "1";
    } catch (e) {
        el.innerHTML = `❌ 加载失败: ${e.message}`;
    }
}

function renderMatrix(matrix) {
    const stages = ["unit", "integration", "system", "acceptance"];
    let html = `<div class="vmatrix"><table>
        <thead><tr>
            <th>REQ</th><th>V 阶段</th><th>commit</th><th>test</th>
            ${stages.map(s => `<th>${s}</th>`).join("")}
        </tr></thead><tbody>`;
    for (const r of matrix) {
        html += `<tr>
            <td><strong>${r.req_id}</strong></td>
            <td><span class="vphase-tag">${r.v_phase}</span></td>
            <td>${r.commit_count}</td>
            <td>${r.test_count}</td>
            ${stages.map(s => {
                const st = r.stages[s] || "pending";
                return `<td><span class="stage-cell stage-${st}">${st}</span></td>`;
            }).join("")}
        </tr>`;
    }
    html += "</tbody></table></div>";
    return html;
}

// 追溯详情
document.getElementById("trace-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const reqId = document.getElementById("trace-req-id").value.trim();
    if (!reqId) return;
    const el = document.getElementById("trace-content");
    el.innerHTML = "🔍 查询中...";
    try {
        const resp = await fetch(`${API}/api/traceability/${reqId}`);
        const data = await resp.json();
        if (data.error) {
            el.innerHTML = `<p style="color: var(--fail);">❌ ${data.error}</p>`;
            return;
        }
        el.innerHTML = renderTrace(data);
    } catch (e) {
        el.innerHTML = `❌ 查询失败: ${e.message}`;
    }
});

function renderTrace(t) {
    const req = t.requirement || {};
    return `
        <div class="trace-card">
            <h3>${req.id} — ${escapeHtml(req.text)}</h3>
            <p><span class="vphase-tag">${req.v_phase}</span> 优先级: ${req.priority} | 状态: ${req.status}</p>
        </div>
        <div class="trace-card">
            <h3>📝 Commits (${t.commits.length})</h3>
            <ul>${t.commits.map(c => `<li><code>${c.sha.slice(0, 8)}</code> ${escapeHtml(c.message)} <em>(${c.author})</em></li>`).join("") || "<li>无</li>"}</ul>
        </div>
        <div class="trace-card">
            <h3>🧪 Tests (${t.tests.length})</h3>
            <ul>${t.tests.map(tt => `<li><span class="vphase-tag">${tt.stage}</span> ${escapeHtml(tt.test_path)}</li>`).join("") || "<li>无</li>"}</ul>
        </div>
        <div class="trace-card">
            <h3>⚙️ CI Runs (${t.ci_runs.length})</h3>
            <ul>${t.ci_runs.map(r => `<li><span class="stage-cell stage-${r.status}">${r.stage}</span> ${r.status} | ${escapeHtml(r.pipeline_run)}</li>`).join("") || "<li>无</li>"}</ul>
        </div>
    `;
}

// meta CI
async function loadMetaCI() {
    const el = document.getElementById("meta-content");
    el.innerHTML = "加载中...";
    try {
        const resp = await fetch(`${API}/api/meta-ci`);
        const data = await resp.json();
        if (!data.configs || data.configs.length === 0) {
            el.innerHTML = `<p style="color: #757575;">meta CI 暂无记录。Tekton PipelineRun 跑过会自动写入。</p>`;
            return;
        }
        el.innerHTML = data.configs.map(c => `
            <div class="trace-card">
                <code>${c.sha.slice(0, 8)}</code> <strong>${escapeHtml(c.path)}</strong>
                — <span class="stage-cell stage-${c.ci_self_test === 'pass' ? 'pass' : 'fail'}">${c.ci_self_test}</span>
            </div>
        `).join("");
    } catch (e) {
        el.innerHTML = `❌ 加载失败: ${e.message}`;
    }
}

// AI 解读
document.getElementById("explain-all").addEventListener("click", async () => {
    const el = document.getElementById("explain-content");
    el.innerHTML = "🔄 LLM 解读中（可能 30s+）...";
    try {
        const resp = await fetch(`${API}/api/ci/explain-all`);
        const data = await resp.json();
        el.innerHTML = `<div class="markdown-body">${renderMarkdown(data.markdown)}</div>`;
    } catch (e) {
        el.innerHTML = `❌ 解读失败: ${e.message}`;
    }
});

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
    }[c]));
}

function renderMarkdown(md) {
    return md.split("\n").map(line => {
        line = line.trim();
        if (line.startsWith("## ")) return `<h2>${escapeHtml(line.slice(3))}</h2>`;
        if (line.startsWith("### ")) return `<h3>${escapeHtml(line.slice(4))}</h3>`;
        if (line.startsWith("- ")) return `<li>${escapeHtml(line.slice(2))}</li>`;
        if (line === "") return "";
        if (line.startsWith("```")) return `<pre>${escapeHtml(line)}</pre>`;
        return `<p>${escapeHtml(line)}</p>`;
    }).join("\n").replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`);
}

// 首次加载
loadMatrix();
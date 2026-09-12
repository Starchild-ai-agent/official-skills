# GPT-Live Demo 部署指南

## 本地开发（最快路径）

```bash
# 进入 skill 的 scripts 目录
cd <skill-dir>/scripts

# 安装依赖（首次）
npm install

# 设置 API Key（需要 gpt-live-1 Beta 访问权限）
export OPENAI_API_KEY=sk-...

# 启动
node server.mjs
# → Listening on :3000

# 打开浏览器
open http://localhost:3000
```

**前提**：Starchild agent 的 SSE 流端点须在 `localhost:8000/chat/stream` 运行。
在 Starchild 平台内 skill 运行时该端点自动可用；独立部署时需手动启动 agent。

---

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | 需要 gpt-live-1 访问权限（Beta） |
| `PORT` | 否 | HTTP 监听端口，默认 3000 |

---

## 在 Starchild Preview 中运行

```bash
# 在 workspace 中启动 node server（后台）
node skills/gpt-live-demo/scripts/server.mjs &
```

然后用 `preview` 工具 serve port 3000，用户通过 `/preview/<id>/` 访问。
注意 WebRTC 需要 HTTPS；Starchild preview 已自动提供 HTTPS。

---

## 公网发布（Starchild 内）

预览跑起来后，用 community-publish skill 的 `publish_preview` 一键发到公网：

```python
from core.skill_tools import community_publish as cp
cp.publish_preview("7120-gpt-live-demo", slug="gpt-live-demo", title="GPT-Live 语音 Demo")
# → https://7120-gpt-live-demo.community.iamstarchild.com/
```

注意：公网开放后 `/api/session` 无鉴权，任何访客都会消耗你的 OpenAI quota；
长期公开建议加 Bearer token。容器休眠时公网访客会看到 offline 页面。

---

## Fly.io 生产部署

### 1. 创建 Dockerfile

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev
COPY server.mjs index.html ./
ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.mjs"]
```

### 2. fly.toml

```toml
app = "gpt-live-demo"
primary_region = "nrt"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[[vm]]
  memory = "256mb"
  cpu_kind = "shared"
  cpus = 1
```

### 3. 部署

```bash
cd skills/gpt-live-demo/scripts
fly launch --no-deploy   # 首次，生成配置
fly secrets set OPENAI_API_KEY=sk-...
fly deploy
```

> ⚠️ 生产部署前必须在 `/api/session` 路由添加鉴权（Bearer token 或 session cookie），
> 否则任何人均可消耗你的 OpenAI quota。

---

## Nginx 反向代理（已有服务器）

```nginx
server {
    listen 443 ssl;
    server_name live.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
    }
}
```

WebRTC 不走 Nginx（直接 STUN/ICE），只有 `/api/session` 的 SDP 协商走代理。

---

## 故障排查

| 现象 | 原因 | 解法 |
|------|------|------|
| `OPENAI_API_KEY not set` | 环境变量未传入 | `export OPENAI_API_KEY=sk-...` |
| `gpt-live-1` 403 | 无 Beta 访问权限 | 申请 OpenAI GPT-Live Beta |
| 页面可访问但无法建立通话 | 非 HTTPS 导致浏览器拒绝麦克风 | 用 localhost 或 HTTPS 域名 |
| 委派后大脑无回复 | `localhost:8000` 未运行 | 确认 Starchild agent 在运行 |
| session.commentary 无声音 | DataChannel 未开放 | 检查 WebRTC 协商是否成功 |

---

## 修改语音 Prompt

编辑 `server.mjs` 中的 `LIVE_PROMPT` 常量（约第 10 行），重启服务即生效。
不建议修改 `delegation` 配置（`type: "client"`），除非改为 Responses 模式。

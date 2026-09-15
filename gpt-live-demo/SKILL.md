---
name: gpt-live-demo
version: 0.5.0
description: >
  GPT-Live 语音接线员 Demo — WebRTC 语音通话前端 + Express 中继服务器 + Starchild brain 桥接。
  客户端委托（Live 端零工具）+ Binding 抽象：core（三通道封装/转写/委托器）· bindings（thread，可扩 onboarding/orchestrator）· adapters（Starchild runtime）。
  ?binding=thread&thread_id= 绑定 Starchild thread：以 thread 为唯一上下文源——启动灌快照、委托进 thread、语音专属轮写回、thread 事件回流 Live。
  用户通过浏览器直接与 GPT-Live 语音模型对话，对话内容由 Starchild agent 作为后端大脑处理。
  适用于：语音 Demo 演示、GPT-Live 中继服务开发、实时语音 + AI 代理集成原型。
tags: [voice, gpt-live, webrtc, demo, relay-server]
author: Starchild
---

# GPT-Live 语音接线员 Demo

## 概述

本 skill 封装了一个完整的 GPT-Live WebRTC 语音 Demo：

- **Web 前端**（`scripts/index.html`）：纯浏览器 WebRTC 客户端，含通话控制、事件日志、按秒计费显示
- **中继服务器**（`scripts/server.mjs`）：Node.js/Express，负责向 OpenAI 申请 WebRTC session 并将委派任务转发给 Starchild agent
- **部署说明**（`references/deploy.md`）：本地开发与生产部署步骤

## 架构

```
浏览器 index.html      仅 WebRTC：DataChannel 事件 → POST /api/bridge/:id/event；SSE /api/bridge/:id/out → dc.send()
server.mjs             薄壳：POST /api/session {sdp, binding, ...params} 选 binding → seed → OpenAI live.create
core/live-session.mjs  三通道封装 think(text,id) / say(text,id) / instruct(text)；≤1500 字切片；null-id thinking 合并节流 ≤1/1.5s
core/transcripts.mjs   DataChannel 事件 → 完整的 user / live 轮次（宽匹配 input|output.*transcript + completed|done|final）
core/delegator.mjs     delegation.created → binding.handle(text) → think/say(id)；1.5s 内无委托的用户轮 → onUserTurn；插话 → interrupt
bindings/thread.mjs    ThreadBinding：seed（最近 10 轮 + 在跑 run + 语音尾部，≤9000 字，最旧先丢）· handle（/chat/stream {thread_id}）· 写回缓冲 · events（/push/events）· interrupt
adapters/starchild-runtime.mjs  唯一知道 :8000 的文件：resolveSession / messages / runs / chat / cancelRun / events
```
依赖只向下：core 不知道 Starchild，bindings 不知道 WebRTC。加场景 = 加一个 binding 文件 + 在 bindings/index.mjs 注册 + URL 参数 `?binding=<kind>`。
Live 端 **没有工具**（OpenAI client delegation 规范：`session.delegation.created` 只带元数据，业务规则与工具留在后端）。

## 快速开始

### 1. 安装依赖

```bash
cd <skill-dir>/scripts
npm install
```

### 2. 准备 OpenAI API key（安装者必读）

本 skill 依赖 OpenAI 的 `gpt-live-1` 实时语音模型，**没有内置 key，也无法代申请**。
使用前请自行准备：

1. 前往 https://platform.openai.com/api-keys 创建一个 API key（`sk-...` 格式）；
2. 该账号需已开通 **gpt-live-1（Realtime Beta）访问权限**——在 OpenAI 后台申请，未开通会报 403/model_not_found；
3. 将 key 写入环境变量（或 skill 目录下的 `.env`）：

```bash
export OPENAI_API_KEY=sk-...   # 必填，需 gpt-live-1 访问权限
export PORT=3000               # 可选，默认 3000
```

> 没有有效 key 时，`/api/session` 会返回 401，浏览器端表现为"无法开始通话"。

### 3. 启动服务

```bash
node server.mjs
```

然后打开 `http://localhost:3000` 即可开始语音通话。

> **前提**：Starchild agent 的 `/chat/stream` 端点须在 `localhost:8000` 运行；
> 若你在 Starchild 平台内使用本 skill，该端点已自动可用。

## 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/server.mjs` | HTTP 壳：/api/session · /api/bridge/:id/{event,out} · /api/seed（调试）· /api/health |
| `scripts/index.html` | 纯 WebRTC 前端，无业务逻辑 |
| `scripts/core/*` | 协议层，与 Starchild 无关 |
| `scripts/bindings/*` | 场景层；`index.mjs` 为注册表 |
| `scripts/adapters/starchild-runtime.mjs` | runtime HTTP 客户端 |
| `scripts/data/voice-log.json` | 过渡件：Live 自答轮次的写回缓冲（runtime 提供 append-message 后删除） |
| `references/api-notes.md` | API 细节、已知坑、runtime 侧待补接口 |

## 使用本 skill 的场景

当用户要求：
- 启动 / 演示 GPT-Live 语音 Demo
- 修改语音接线员的系统提示（`LIVE_PROMPT`）
- 调整 delegation 策略（何时委派给 Starchild brain）
- 部署到生产（Fly.io / Docker / Nginx 反代）

→ 读 `references/deploy.md` 获取完整步骤。

## Thread 绑定模式

URL：`/?binding=thread&thread_id=<thread uuid>`（全屏标签页，需麦克风权限）。

- 建连：thread 最近 10 轮 + 在跑 run 数 + 尚未写回的语音轮压缩成快照灌 `session.input`；
- 委托：一切需要事实/工具/文件/写作/决策的话进同一 thread（runtime 写入用户轮与回答，网页可见）；
- 写回：Live 自己答掉的轮次先记入 `data/voice-log.json`，下次委托时补交；
- 回流：thread 事件以 `thinking.append(null)` 静默注入，合并节流；
- 打断：只有 runtime 确认取消才对 Live 说「已停」（当前 run_id 未返回 → 始终按「仍在跑」处理）。

验收：A1 开场复述当前目标；A2 语音一句 → 文字页出现；A3 文字页打字 → 语音能答「刚打了什么」；A4 闲聊本地答/事实类委托；A5 重开页面 A1 仍过；A6 委托首句 ≤3s。

## 注意事项

- 使用前必须自备 `OPENAI_API_KEY`（见「快速开始 · 第 2 步」），需开通 gpt-live-1（Realtime Beta）访问权限，否则无法建立通话
- 服务默认仅监听本地，生产部署前须在 `/api/session` 加鉴权
- 任务与语音历史持久化到 `data/` 目录（防抖落盘），重启不丢失；完成后任务保留 1 小时
- 计费估算基于 $0.05/分钟（gpt-live-1 语音），后端 brain 调用费用另计

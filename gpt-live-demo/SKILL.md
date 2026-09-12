---
name: gpt-live-demo
version: 0.2.1
description: >
  GPT-Live 语音接线员 Demo — WebRTC 语音通话前端 + Express 中继服务器 + Starchild brain 桥接。
  五工具路由（ask_starchild / check_task / cancel_task / list_tasks / memory_lookup）、
  跨重启持久化（data/tasks.json + voice-history.json）与会话记忆回灌。
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
浏览器 (index.html)
  │  WebRTC audio
  │  DataChannel (oai-events)
  ▼
OpenAI GPT-Live (gpt-live-1)
  │  client delegation 事件
  ▼
server.mjs (/api/agent)
  │  HTTP SSE stream
  ▼
Starchild agent (localhost:8000/chat/stream)
  │  结果回传
  ▼
GPT-Live → 语音播报
```

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

| 文件 | 说明 |
|------|------|
| `scripts/server.mjs` | Express 中继服务器（WebRTC session 代理 + brain 桥接） |
| `scripts/index.html` | 浏览器前端（WebRTC + UI + 计费器） |
| `scripts/package.json` | Node.js 依赖（express, openai） |
| `references/deploy.md` | 本地开发与生产部署完整指南 |
| `references/api-notes.md` | GPT-Live delegation API 要点与已知坑 |

## 使用本 skill 的场景

当用户要求：
- 启动 / 演示 GPT-Live 语音 Demo
- 修改语音接线员的系统提示（`LIVE_PROMPT`）
- 调整 delegation 策略（何时委派给 Starchild brain）
- 部署到生产（Fly.io / Docker / Nginx 反代）

→ 读 `references/deploy.md` 获取完整步骤。

## 注意事项

- 使用前必须自备 `OPENAI_API_KEY`（见「快速开始 · 第 2 步」），需开通 gpt-live-1（Realtime Beta）访问权限，否则无法建立通话
- 服务默认仅监听本地，生产部署前须在 `/api/session` 加鉴权
- 任务与语音历史持久化到 `data/` 目录（防抖落盘），重启不丢失；完成后任务保留 1 小时
- 计费估算基于 $0.05/分钟（gpt-live-1 语音），后端 brain 调用费用另计

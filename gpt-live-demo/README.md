# gpt-live-demo-skill

> **GPT-Live 语音接线员 Demo** — Starchild Skill

WebRTC 语音通话前端 + Express 中继服务器，让用户通过浏览器与 GPT-Live（gpt-live-1）语音模型对话，后端大脑由 Starchild agent 提供。

## 一行安装（任意 Starchild agent）

```bash
npx skills@latest add jotaro-ora/gpt-live-demo-skill --agent openclaw
```

## 快速启动

```bash
cd scripts
npm install
export OPENAI_API_KEY=sk-...
node server.mjs
# 打开 http://localhost:3000
```

## 架构

```
浏览器 (index.html)
  │  WebRTC audio + DataChannel
  ▼
OpenAI GPT-Live (gpt-live-1)
  │  client delegation 事件
  ▼
server.mjs (/api/agent)
  │  HTTP SSE stream
  ▼
Starchild agent (localhost:8000/chat/stream)
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | Skill 元数据和使用文档 |
| `scripts/server.mjs` | Express 中继服务器 |
| `scripts/index.html` | WebRTC 前端 |
| `scripts/package.json` | 依赖声明 |
| `references/deploy.md` | 完整部署指南 |
| `references/api-notes.md` | GPT-Live API 要点与已知坑 |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | 需要 gpt-live-1 Beta 访问 |
| `PORT` | 否 | 端口，默认 3000 |

---

Co-authored-by: Starchild <noreply@iamstarchild.com>

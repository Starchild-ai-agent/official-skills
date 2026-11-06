# GPT-Live API 要点与已知坑

## delegation 模式

本 Demo 使用 `"type": "client"` delegation（客户端委派）：
- GPT-Live 在需要外部信息时，通过 DataChannel 发送 `session.delegation.created` 事件
- 客户端（index.html）截获事件，调用本地 `/api/agent` 端点
- 中继服务器将用户文字转发给 Starchild brain，轮询结果后用 `session.commentary.append` 回传
- GPT-Live 将 commentary 内容读出来播放给用户

对比 `"type": "responses"`（服务端委派）：
- Responses 模式由 OpenAI 直接调用你的 Responses model，无需客户端轮询
- Client 模式更灵活，可接入任意后端（包括 Starchild streaming）

## 关键 DataChannel 消息类型

```json
// 推送中间进度（让 GPT-Live 知道大脑在思考）
{"type": "session.thinking.append", "delegation_id": "...", "content": "调用工具..."}

// 推送最终结果（GPT-Live 会把这段话说出来）
{"type": "session.commentary.append", "delegation_id": "...", "content": "最终答案..."}

// 主动结束会话
{"type": "session.close"}
```

## 已知坑

### 1. utterBuf 时序问题
`session.delegation.created` 触发时，用户的输入转写（`input.audio.transcription.delta`）
可能还没全部到达。Demo 用 `utterBuf` 累积，delegation 触发时一次性读取。
**若用户说话很快，可能丢失最后几个字**。生产环境建议等 `input.audio.transcription.completed`。

### 2. delegation_id 可能为 null
部分版本的 GPT-Live 在 `session.delegation.created` 里 `delegation_id` 字段路径不固定，
Demo 做了防御：`d.id || ev.delegation_id || ""`。

### 3. commentary 字数限制
`session.commentary.append` 的 content 建议不超过 2000 字符；过长可能被截断或超时。
Demo 已做 `.slice(0, 2000)` 截断。

### 4. 计费修正
`session.closed` 事件里的 `usage` 字段键名不固定（目前文档未明确）。
Demo 用正则 `/second(s)?$/i` 防御性解析，找到第一个数字型 `*seconds` 字段。

### 5. gpt-live-1 模型访问
截至 2026 年，`gpt-live-1` 仍需申请 Beta 访问权限。
错误表现：POST `/api/session` 返回 403 或 404。

## Thread 绑定模式（v0.3）—— Starchild thread 为唯一事实源

前端 URL 加 `?thread_id=<thread uuid 或完整 session id>` 即进入 thread 模式：

| 环节 | 实现 | 说明 |
|---|---|---|
| 启动快照 | `POST /api/session {thread_id}` → 中继 `GET <runtime>/session?session_id=` → 最近 10 轮（每条 ≤400 字）作 developer message 灌 `session.input` | 不再用 voice-history 回灌；`GET /api/thread-snapshot?thread_id=` 可预览灌入内容 |
| 委托 | `POST /api/agent {thread_id,text}` → runtime `/chat/stream {message, thread_id}` | **不再拼历史**——runtime 自己持有 thread；用户轮与回答由 runtime 写入 thread |
| 语音专属轮写回 | 前端在 `input…transcription completed` 后 1.5s 内无 delegation → `POST /api/voice-log {role:"user"}`；Live 说出的话 `output…completed` → `{role:"live"}` | runtime 暂无 append-message API，故先记在 `data/voice-log.json`，下次 delegation 时作为 `[Voice-only exchanges…]` 前缀交给 brain 并标记 delegated |
| thread 事件回流 | 中继按 thread 订阅 `<runtime>/push/events?session_id=` 缓冲；前端每 2s `GET /api/thread-events?since=` → `session.thinking.append(delegation_id:null)` | 静默注入，≤1 条/1.5s、合并、≤1500 字；建连时跳过历史事件 |
| thread 忙碌 | `/chat/stream` 返回空流 | 已实测：thread 正在跑别的 run 时 runtime 会把消息**并入该 run**，答案落在 thread 而非本 SSE；中继此时回一句"已并入，稍后在对话里出现"，避免 Live 沉默 |

`resolveSession`：`/sessions` 列表有上限、可能漏掉最活跃的 thread，所以先从列表里任一 thread 推出 `agent:main:thread:<N>` 前缀，直接 `GET /session` 探测；可用 `STARCHILD_THREAD_PREFIX` 覆盖。runtime 地址由 `STARCHILD_RUNTIME`（默认 `http://localhost:8000`）指定。

未在 P0 核实、需实测：`session.input` 的 token 上限；转写 completed 事件的精确类型名（前端按 `/input.*transcri/` + `/completed|done|final/` 宽匹配）。

## 会话历史与持久化设计（无 thread_id 的 legacy 模式）

服务器维护全局语音历史（`voiceHistory`，所有语音会话共享一个 `voice` 流，最多 40 条）。
每次建会话时把最近 12 条历史以 developer message 回灌进 GPT-Live session（记忆回灌），
每次 delegation 触发时再把最近 10 条拼接到 brain 的 prompt 前缀。

持久化：任务（`data/tasks.json`，完成后保留 1 小时）与语音历史（`data/voice-history.json`）
均防抖落盘，重启不丢失。`data/` 目录不入库（见 .gitignore）。

## 异步任务轮询模式

`/api/agent` 路由采用异步模式（防止 Fly.io / Nginx 504）：
1. 前端 POST `/api/agent`，立即返回 `{task_id}`
2. 后台开始流式调用 `localhost:8000/chat/stream`
3. 前端每 2 秒 GET `/api/agent/:id` 轮询状态
4. 每解析到一条进展事件就通过 DataChannel 推送 `session.thinking.append`
5. 任务完成后前端读取 `reply`，推送 `session.commentary.append`
6. 任务结果落盘 `data/tasks.json`，完成后保留 1 小时，可查询/取消（`/api/tasks`、`/api/tasks/:id/cancel`）

## 内建后台工具

服务器为 GPT-Live 提供五个工具端点：`ask_starchild`（委派大脑）、`check_task`、
`cancel_task`、`list_tasks`（以上走 `/api/agent*` 与 `/api/tasks*`）、
`memory_lookup`（`/api/memory`，按关键词检索持久化语音历史）。

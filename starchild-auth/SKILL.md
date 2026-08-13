---
name: starchild-auth
version: 1.10.1
description: |
  Starchild Auth SDK: add OAuth login to any web app with one SDK.

  Use when integrating Starchild login into a project (e.g. add Starchild sign-in to my React app, set up OAuth with iamstarchild.com, implement login/logout with Starchild Auth SDK).
  Also use for local OAuth/CORS testing guidance (localhost:6066 web, third-party localhost origins, browser vs Node).
author: starchild
tags: [auth, oauth, login, sdk, react, vue, html]
metadata:
  starchild:
    emoji: "\U0001F511"
    skillKey: starchild-auth
---

# 🔑 Starchild Auth SDK — 完整开发指南

Integrate Starchild OAuth login into any web application. The SDK handles OAuth popup flow, token refresh, unified `StarchildAuthError`, namespaced helpers (`auth.chat` / `auth.credit` …), and 60+ API methods for full Agent access.

### 版本策略

| 产物 | 当前版本 | 何时 bump |
|------|---------|-----------|
| npm `starchild-auth-sdk` | **0.4.1** | 代码 / 公开 API 变更 |
| 本 Skill `starchild-auth` | **1.10.1** | 集成指南 / 场景文档变更（可与 package 独立） |

两套 semver **互不绑定**：只改文档可只升 skill；只改实现必须升 package（skill 通常同步升 minor/patch 说明新能力）。

---

## 架构概览

```
第三方网站 (your-app.com)
    │
    ├─ StarchildAuth SDK (starchild-auth-sdk)
    │   ├─ auth.login()       → 弹出 starchild-web 授权页面
    │   ├─ auth.logout()      → go-api POST /v1/oauth/logout
    │   ├─ auth.bindAccount() → 跳转主站 Linked accounts 绑定正式账号
    │   └─ token refresh      → go-api POST /v1/oauth/refresh
    │
    ├─ API 调用 (chat scope)
    │   ├─ chat/stream      → clawd (SSE 流式响应)
    │   ├─ /api/clawd/*     → ai-agent (线程/消息)
    │   ├─ /api/cloud/*     → ai-agent (容器管理)
    │   └─ WebSocket        → clawd (文件同步/终端/指标)
    │
    ├─ Credits API (credit:read / credit:write)
    │   └─ https://credit.iamstarchild.com
    │       ├─ GET  /api/credits|charges|topups|usage/daily|pending|tx/{hash}
    │       ├─ POST /api/stripe/create-session | gift-cards/redeem | points/exchange
    │       ├─ GET/POST /api/kyc/* | /api/referral/* | /api/migration/reward/*
    │       └─ GET  /api/public/users/{id}/woo-bonus
    │
    └─ 用户信息
        └─ /v1/oauth/userinfo → ai-agent
```

## 应用注册与审核

### 注册流程

1. 在 [iamstarchild.com](https://iamstarchild.com) → More → **OAuth Apps** → Create App
2. 填写信息：
   - **Name** *(必填)*: 应用名称
   - **Allowed Origin** *(必填)*: **第三方应用自己的页面 Origin**（不是 starchild-web）。例：生产 `https://your-app.com`；本地 `http://localhost:5173` / `http://localhost:3333`。只允许 origin（scheme://host[:port]，无路径/query/hash）；非 localhost 必须 `https://`。可配多个。**不要**把 `http://localhost:6066` 当成第三方 origin——6066 是主站 web 本地端口，已在服务端静态 CORS 中放行。
   - **Scopes**: 勾选需要的权限
   - **System Prompt** *(可选)*: 自定义 Agent 行为
3. 仅选 `profile` → 自动通过，立即获得 Client ID
4. 选了 `chat` / `credit:read` / `credit:write` → 进入**管理员审核**，审核通过后才生成 Client ID

### Scope 权限体系

| Scope | 权限范围 | 审核 |
|-------|---------|:--:|
| `profile` | 查看用户名、头像、ID | 自动通过 |
| `chat` | Agent 对话、线程管理、容器管理、技能、媒体、定时任务、钱包读取、计费、WebSocket | 需审核 |
| `credit:read` | 查看 Credits 余额和账户状态 | 需审核 |
| `credit:write` | 充值/购买 Credits、兑换 Points（隐含 credit:read） | 需审核 |

> **注意**: 容器**删除**操作对所有 OAuth token 均被拦截（返回 403）。这是服务端硬限制。

---

## 安装

### npm / yarn / pnpm

```bash
npm install starchild-auth-sdk
# or: yarn add starchild-auth-sdk
# or: pnpm add starchild-auth-sdk
```

### CDN (plain HTML)

```html
<!-- UMD build — use with plain <script> tags -->
<script src="https://unpkg.com/starchild-auth-sdk/dist/starchild-auth.umd.cjs"></script>

<!-- China mirror -->
<script src="https://registry.npmmirror.com/starchild-auth-sdk/latest/files/dist/starchild-auth.umd.cjs"></script>
```

> UMD 构建导出 `window.StarchildAuth`（构造函数本身，不是 namespace）。
> ESM 构建 (`starchild-auth.js`) 用于 `<script type="module">` 或 bundler。

---

## 初始化与登录

```typescript
import { StarchildAuth } from 'starchild-auth-sdk'

const auth = new StarchildAuth({
  clientId: 'your-client-id',          // 必填
  scope: 'profile chat credit:read credit:write', // 空格分隔；需要 Credits 时加上 credit scopes
  // clawdApiBase: 'https://preview.iamstarchild.com', // chat/stream HTTP
  // clawdWsBase: 'wss://preview.iamstarchild.com',   // /ws/sync|terminal|metrics
  // creditApiBase: 'https://credit.iamstarchild.com', // 可选，默认生产域名

  // 登录成功回调（popup 或 autoLogin 恢复 session 时触发）
  onLogin: ({ accessToken, refreshToken, expiresIn, userInfo }) => {
    console.log('Logged in:', userInfo.agentName, 'guest=', userInfo.isGuest)
    // userInfo = { userInfoId, agentName, agentAvatar, isGuest }
  },

  onLogout: () => { /* 清除本地状态 */ },
  onTokenRefresh: (newToken) => { /* 更新本地 token */ },
  onTokenRefreshFailed: () => { /* session 过期 */ },

  // 可选配置
  autoLogin: true,          // 默认 true — 从 localStorage 恢复 session
  origin: 'https://iamstarchild.com',  // Starchild 站点
  refreshInterval: 720000,  // 自动刷新间隔 (ms)，默认 12 分钟
})
```

### Token 生命周期

- **Access Token**: 15 分钟有效，自动每 12 分钟刷新；`auth.getToken()`
- **Refresh Token**: 7 天有效，存储在 `localStorage` 的 `starchild_rt_{clientId}` key 中；`auth.getRefreshToken()` 仅暴露内存中的同一值
- **autoLogin**: 页面加载时自动用 refresh token 恢复 session
- **visibilitychange**: 从后台切回时自动刷新 token

#### `getRefreshToken()` 安全模型

- Refresh token **本来就**写在集成方 origin 的 `localStorage`（autoLogin 需要）；公开 getter **不扩大**威胁面，只是可读内存副本。
- **优先**让 SDK 自己刷新：`refreshToken()` / 定时 auto-refresh / visibility 刷新。
- 若你拷贝到自有存储：当作密码——禁止日志、禁止发给第三方后端、禁止放进 URL。
- 集成方 origin 上的 XSS 本来就能读 `localStorage`；用 CSP、避免 inline script 缓解。

### Guest 账号与绑定正式登录方式

> **没有 `loginAsGuest()`**。Guest 与正式账号走**同一条** `auth.login()` 主站 popup 流程；用户在主站选择 continue-as-guest（或等价入口）时才会拿到 `isGuest: true`。第三方不要自建 guest 登录。

OAuth 登录可能返回 **Guest（临时）账号**（`userInfo.isGuest === true`）。Guest 可正常使用已授权 scope，但未绑定永久登录方式（Google / X / Email / Phone / Wallet）。

**绑定必须在 Starchild 主站完成**，第三方不要自建绑定页。SDK 提供跳转方法：

```typescript
// 登录后检查是否为 Guest
const user = auth.getUserInfo()
// 或刷新：const user = await auth.fetchUserInfo()

if (auth.isGuest() || user?.isGuest) {
  // 打开主站 Account management → Linked accounts
  // URL: https://iamstarchild.com/?account_tab=linked-accounts
  const win = auth.bindAccount()
  if (!win) {
    // 弹窗/新标签被拦截时，可自行跳转
    window.location.href = auth.getBindAccountUrl()
  }
}

// 仅需要 URL（例如自己渲染按钮 href）
const bindUrl = auth.getBindAccountUrl()
// => `${origin}/?account_tab=linked-accounts`
```

| 方法 | 返回 | 说明 |
|------|------|------|
| `isGuest()` | `boolean` | 当前用户是否为 Guest；未登录为 `false` |
| `getBindAccountUrl()` | `string` | 主站绑定页 URL（Linked accounts tab） |
| `bindAccount()` | `Window \| null` | 新标签打开主站绑定流；被拦截时返回 `null` |

> 主站打开后会根据 `?account_tab=linked-accounts` 自动打开账号管理并切到 **Linked accounts**。用户完成绑定后，第三方应用下次 `fetchUserInfo()` / token refresh 后应看到 `isGuest: false`。

---

## 核心 API 调用模式

### 请求格式

所有 SDK 方法自动处理 token 注入。手动发送请求时：

```typescript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json',
}
```

> **clawd 端点必须带 `fly-force-instance-id`**：clawd（`preview.iamstarchild.com`）每个 Fly Machine 是单用户容器，容器归属（IDOR）检查要求请求落到当前用户容器，否则返回 403「Access denied: you do not own this resource」。OAuth access token 不含 `containerId`，SDK 会自动通过 `GET /api/cloud/containers` 解析并注入 `fly-force-instance-id: <container_id>` header；手动 curl 测 clawd 端点时需显式带该 header，否则会 403。

**端点地址**：
- ai-agent REST API: `https://ai-api.iamstarchild.com`（线程/消息/容器/技能等）
- clawd HTTP API: `https://preview.iamstarchild.com`（chat/stream、scheduled-jobs、models）
- Token 端点: `https://go-api.iamstarchild.com/v1`（go-api）

---

## 命名空间 API（兼容层）

Flat 方法全部保留。命名空间是 plan 303 风格的分组别名，二者等价：

```typescript
await auth.sendMessage('hi')
await auth.chat.send('hi')          // alias

await auth.getCredits()
await auth.credit.getBalance()      // alias

await auth.listThreads()
await auth.threads.list()
```

| Namespace | 主要方法 |
|-----------|---------|
| `auth.profile` | `fetchUserInfo`, `getUserInfo`, `isGuest`, `bindAccount`, `getBindAccountUrl` |
| `auth.chat` | `send`/`sendMessage`, `reconnect`/`reconnectStream`, `cancelRun`, `getModel`/`setModel`, WS factories |
| `auth.threads` | `create`, `list`, `get`, `delete`, `search`, `pin`, `updateTitle` |
| `auth.messages` | `list`, `delete` |
| `auth.containers` | `list`, `status`, `metrics`, `deploy`, `start`, `stop`, `restart`, `wake`, `rename`, `delete`, … |
| `auth.skills` | `catalog`, `search`, `detail` |
| `auth.media` | `uploadImage`, `transcribeAudio`, `synthesizeSpeech` |
| `auth.shares` | `create`, `list`, `get`, `delete`, `fork` |
| `auth.feedback` | `rate`, `delete` |
| `auth.jobs` | `list`, `create`, `get`, `pause`, `resume`, `restart` |
| `auth.wallet` | `getPortfolio`, `list`, `create`, `delete`, `exportPrivateKey`, `createOnrampSession` |
| `auth.credit` | 余额/流水/Stripe/礼品卡/**Points**/**KYC**/**Referral**/migration/WOO（见场景八） |

> Points 兑换、KYC、Referral **已对 OAuth 开放**（需 `credit:read` / `credit:write`），不是主站专属。

---

## 场景一：发送消息并读取 SSE 流响应

这是最核心的交互模式。消息通过 SSE (Server-Sent Events) 流式返回。

### SDK 方式

```typescript
const stream: Response = await auth.sendMessage('Hello, analyze this data')

// SSE 是流式响应，需要逐块读取
const reader = stream.body!.getReader()
const decoder = new TextDecoder()
let buffer = ''

while (true) {
  const { done, value } = await reader.read()
  if (done) break

  buffer += decoder.decode(value, { stream: true })
  const lines = buffer.split('\n')
  buffer = lines.pop() || ''  // 保留未完成的行

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6))
      // event.type 决定处理方式
      handleStreamEvent(event)
    }
  }
}
```

### 原生 fetch 方式（不使用 SDK）

```typescript
// POST /chat/stream — SSE 流式聊天（clawd 端点）
const response = await fetch('https://preview.iamstarchild.com/chat/stream', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Hello, analyze this data',
    thread_id: threadId,    // 可选，不传则创建新 thread
  }),
})

// 读取 SSE 流（同上）
```

### SSE 事件类型

| Event Type | 含义 | 关键字段 |
|-----------|------|---------|
| `agent_start` | Agent 开始处理 | `session_key` — 用于后续重连 |
| `text_delta` | 文本增量输出 | `text` — 新产生的文本片段 |
| `tool_use` | 调用工具 | `tool_name`, `tool_input` |
| `tool_output` | 工具返回结果 | `tool_output` — 工具输出 |
| `agent_end` | Agent 完成 | `stop_reason` — end_turn / tool_use |
| `error` | 错误 | `message` — 错误描述 |

```typescript
function handleStreamEvent(event: any) {
  switch (event.type) {
    case 'agent_start':
      console.log('Agent started, session:', event.session_key)
      // 保存 session_key 用于断线重连
      break
    case 'text_delta':
      process.stdout.write(event.text)  // 实时输出
      break
    case 'tool_use':
      console.log(`Using tool: ${event.tool_name}(${event.tool_input})`)
      break
    case 'tool_output':
      console.log('Tool result:', event.tool_output)
      break
    case 'agent_end':
      console.log('Done, reason:', event.stop_reason)
      break
    case 'error':
      console.error('Stream error:', event.message)
      break
  }
}
```

### 重连 SSE 流

当 SSE 连接断开（网络问题、页面切换等），用 `session_key` 重连：

```typescript
// POST /chat/stream/reconnect?session_key=xxx&channel=web
const stream = await auth.reconnectStream(sessionKey)
// 读取方式同 sendMessage
```

---

## 场景二：管理对话线程

```typescript
// 创建线程
const thread = await auth.createThread('My analysis')
// thread = { id: string, title: string, created_at: string, ... }

// 列出所有线程
const { threads } = await auth.listThreads()

// 获取线程消息
const { messages } = await auth.listMessages(thread.id, 50)  // 最近 50 条
// messages[0] = { id, role: 'user'|'assistant', content: [...], created_at }

// 搜索线程
const result = await auth.searchThreads('analysis')

// 删除线程
await auth.deleteThread(thread.id)

// 删除消息
await auth.deleteMessages(thread.id)
```

---

## 场景三：管理容器

容器是运行 Agent 的 Fly.io 虚拟机。

```typescript
// 部署新容器
const container = await auth.deployContainer()
// container = { container_id, name, state, region, ... }

// 列出所有容器
const { containers } = await auth.listContainers()

// 获取容器状态
const status = await auth.getContainerStatus(container.container_id)
// status = { state: 'started'|'stopped'|'suspended'|..., ... }

// 启动/停止/重启
await auth.startContainer(container_id)
await auth.stopContainer(container_id)
await auth.restartContainer(container_id)

// 重命名
await auth.renameContainer(container_id, 'production-agent')

// 获取指标
const metrics = await auth.getContainerMetrics(container_id)
// metrics = { cpu: { series: [...] }, memory: { series: [...] }, disk: { series: [...] } }

// ⚠️ 删除容器 — OAuth token 无法执行（服务端返回 403）
// await auth.deleteContainer(container_id)  // 总是失败
```

---

## 场景四：WebSocket 连接

### 实时指标 (CPU/内存/磁盘)

```typescript
const ws = auth.createMetricsWebSocket()

ws.onopen = () => console.log('Metrics connected')
ws.onmessage = (e) => {
  const { cpu_percent, memory_used_bytes, memory_total_bytes, disk_used_bytes } = JSON.parse(e.data)
  console.log(`CPU: ${cpu_percent}%, Mem: ${memory_used_bytes}/${memory_total_bytes}`)
}
ws.onclose = () => console.log('Disconnected — implement reconnection logic')
```

### 文件同步

```typescript
const ws = auth.createSyncWebSocket()

ws.onopen = () => {
  // 订阅文件变更
  ws.send(JSON.stringify({
    type: 'sync:subscribe',
    payload: { paths: ['/src'] }
  }))
}

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data)
  switch (msg.type) {
    case 'sync:connected':
      console.log('Sync ready, session:', msg.payload.sessionId)
      break
    case 'file:created':
      console.log('New file:', msg.payload.path)
      break
    case 'file:updated':
      // msg.payload = { path, type: 'file'|'directory', triggeredBy: 'watcher'|'agent'|'user' }
      console.log('Changed:', msg.payload.path, 'by', msg.payload.triggeredBy)
      break
    case 'file:deleted':
      console.log('Deleted:', msg.payload.path)
      break
    case 'file:moved':
      console.log('Moved:', msg.payload.oldPath, '→', msg.payload.newPath)
      break
  }
}
```

### 终端

```typescript
// sessionId 从 SSE chat stream 的 terminal:connected 事件获取
const ws = auth.createTerminalWebSocket(sessionId)

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data)
  switch (msg.type) {
    case 'connected':
      console.log('Terminal ready, session:', msg.sessionId)
      break
    case 'output':
      process.stdout.write(msg.data)
      break
    case 'error':
      console.error('Terminal error:', msg.message)
      break
  }
}

// 发送命令
ws.send(JSON.stringify({ type: 'input', data: 'ls -la\n' }))
// 调整终端大小
ws.send(JSON.stringify({ type: 'resize', cols: 120, rows: 40 }))
```

### WebSocket 重连

浏览器 WebSocket 不支持自动重连，需要自行实现：

```typescript
class WSReconnect {
  private ws: WebSocket | null = null
  private attempts = 0
  private maxAttempts = 5

  connect(factory: () => WebSocket) {
    this.ws = factory()
    this.ws.onclose = () => {
      if (this.attempts < this.maxAttempts) {
        const delay = Math.min(1000 * 2 ** this.attempts, 30000)
        setTimeout(() => {
          this.attempts++
          this.connect(factory)
        }, delay)
      }
    }
    this.ws.onopen = () => { this.attempts = 0 }
  }
}
```

---

## 场景五：技能与媒体

```typescript
// 浏览技能目录
const catalog = await auth.getSkillsCatalog()
// catalog = { official: [{ source, name, description, ... }], community: [...], installed: [...] }

// 搜索技能
const results = await auth.searchSkills('trading')

// 获取技能详情
const detail = await auth.getSkillDetail('official', 'orderly-trading')

// 上传图片
const image = await auth.uploadImage(base64data, 'image/png')
// image = { url: string, filename: string }

// 语音转文字
const text = await auth.transcribeAudio(audioBase64)
// text = { text: string }

// 文字转语音
const audio = await auth.synthesizeSpeech('Hello world')
// audio = { audio_base64: string, format: 'mp3' }
```

---

## 场景六：分享与反馈

```typescript
// 创建对话分享
const share = await auth.createShare(threadId)
// share = { share_id: string, share_url: string }

const share = await auth.createShare(threadId, ['msg-1', 'msg-2'])  // 指定消息

// 列出分享
const { shares } = await auth.listShares()

// 删除分享
await auth.deleteShare(shareId)

// 复制分享
await auth.forkShare(shareId)

// 点赞/踩消息
await auth.rateMessage(messageId, 'like')
await auth.rateMessage(messageId, 'dislike', 'Not accurate')

// 取消反馈
await auth.deleteFeedback(messageId)
```

---

## 场景七：钱包与计费

```typescript
// 获取投资组合
const portfolio = await auth.getPortfolio()
// portfolio = { total_value_usd, tokens: [...] }

// 列出钱包
const { wallets } = await auth.listWallets()

// 创建/删除钱包
const wallet = await auth.createWallet()
await auth.deleteWallet(walletAddress)

// Coinbase Onramp
const session = await auth.createOnrampSession({
  amount: '100',  // USD
  currency: 'USD',
})
// session = { url: string } — redirect user to this URL
```

---


## 场景八：Credits（余额 / 充值 / Points / KYC / Referral）

> **服务**: `starchild-credit-api`  
> **Base**: `creditApiBase`，默认 `https://credit.iamstarchild.com`  
> **鉴权**: `Authorization: Bearer <oauth_access_token>`  
> **Scope**:
> - `credit:read` — 所有 GET（余额、流水、pending、tx、points 余额、KYC 状态、referral 查询、migration 状态）
> - `credit:write` — 写操作（Stripe 会话、礼品卡、points 兑换、KYC 写、referral bind、migration claim）；**隐含 read**
>
> OAuth App 注册时需勾选对应 scope，审核通过后 token 才会带上。
>
> **开放范围**：余额/流水、Stripe、礼品卡、**Points 兑换**、**KYC**、**Referral**、migration reward、WOO bonus（public）均已对 OAuth 开放；命名空间写法：`auth.credit.*`。

### 初始化

```typescript
const auth = new StarchildAuth({
  clientId: 'your-client-id',
  scope: 'profile chat credit:read credit:write',
  // creditApiBase: 'https://credit.iamstarchild.com', // 默认值，本地可改
  onLogin: ({ userInfo }) => console.log(userInfo),
})
```

### 余额与流水（credit:read）

```typescript
// 当前余额
const bal = await auth.getCredits()
// bal.credit_balance — 可用余额
// bal.pending_credit — 待入账
// bal.total_recharged / bal.total_used
// bal.daily_balance — 订阅日额度（若有）
// bal.container_id / bal.user_id

// 扣费记录（默认近 24h，可分页 + 时间窗）
const charges = await auth.getCreditCharges({
  page: 1,
  page_size: 20,
  start_time: '2026-01-01T00:00:00Z', // 可选 ISO8601
  end_time: '2026-01-31T23:59:59Z',
})
// charges.charges[]: { amount, api_type, balance_after, description, created_at, ... }
// charges.pagination: { page, page_size, has_more }
// charges.time_range: { start_time, end_time }

// 充值记录
const topups = await auth.getCreditTopups({ page: 1, page_size: 20 })
// topups.topups[]: { amount, chain, tx_hash, balance_after, created_at, ... }

// 每日用量
const usage = await auth.getCreditDailyUsage({ days: 7 })
// usage.daily[] / usage.by_api[]

// 待入账
const pending = await auth.getPendingCredit()
// pending.status === 'no_pending' | 'pending_sync' | (有 machine 时直接带 pending_credit)

// 轮询链上/支付 tx
const tx = await auth.getCreditTxStatus(txHash)
// 1) status==='not_detected' && !credited && !pending → 继续轮询
// 2) pending && !container_id → 已进 pending_credit，可停
// 3) pending && container_id → 等 flush，继续轮询
// 4) credited === true → 已入账，停
```

### 字段速查：`CreditBalance`（GET /api/credits）

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | string? | 用户 ID |
| `container_id` | string | 关联容器（可能为空） |
| `credit_balance` | number | 可用 Credits |
| `daily_balance` | number? | 订阅日额度剩余 |
| `total_recharged` | number | 累计充值 |
| `total_used` | number | 累计消耗 |
| `pending_credit` | number? | 待入账 |
| `ipv6` / `name` / `is_active` / `status` / `hint` | optional | 机器/状态信息 |

### Stripe 充值（credit:write）

```typescript
const { url } = await auth.createStripeSession({
  amount_usd: 20,
  success_url: 'https://your-app.com/billing?ok=1',
  cancel_url: 'https://your-app.com/billing?cancel=1',
})
window.location.href = url
// 支付完成后可用 getCreditTxStatus / getCredits / getPendingCredit 确认到账
```

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `amount_usd` | number | 美元金额，如 `10` = $10 |
| `success_url` | string | 支付成功回跳绝对 URL |
| `cancel_url` | string | 取消回跳绝对 URL |

响应：`{ url: string }` — Stripe Checkout 地址。

### 礼品卡（credit:write）

```typescript
const r = await auth.redeemGiftCard('GIFT-CODE-XXX')
// 或 auth.redeemGiftCard({ code: 'GIFT-CODE-XXX' })
// r.amount, r.credited_to: 'machine' | 'pending'
// r.new_balance / r.pending_credit
```

### Points 兑换 Credits（read 查余额 / write 兑换）

```typescript
const pts = await auth.getPointsExchangeBalance()
// pts.available_points, pts.exchange_rate, pts.exchanged_credits, ...

const ex = await auth.exchangePoints(
  { points: 1000 },
  crypto.randomUUID(), // 推荐传 Idempotency-Key，防重试双花
)
// 也可 auth.exchangePoints(1000, idemKey)
// ex.credits_received, ex.new_credit_balance, ex.idempotent?
```

### KYC（points 大额兑换可能要求）

```typescript
const kyc = await auth.getKycStatus()
// kyc.verified / kyc.exempt / kyc.exchanged_credits / kyc.threshold_credits

if (!kyc.verified && !kyc.exempt) {
  const intent = await auth.createKycSetupIntent()
  // intent.client_secret → 交给 Stripe.js / Payment Element 完成绑卡
  // 成功后:
  await auth.verifyKyc(intent.setup_intent_id)
}
```

### Referral

```typescript
const ref = await auth.getReferralStatus()
// ref.my_referral_code, ref.can_bind, ref.has_bound_inviter, ref.invited_by

if (ref.can_bind) {
  await auth.bindReferralCode('INVITE-CODE') // credit:write，仅一次
}

const invitees = await auth.getReferralInvitees()
// invitees.invitees[], invitees.total_bonus_earned, ...
```

### Migration 奖励

```typescript
const st = await auth.getMigrationRewardStatus()
if (st.eligible && !st.already_claimed) {
  const claim = await auth.claimMigrationReward() // credit:write
  // claim.amount, claim.credited_to, claim.new_balance
}
```

### WOO Staking Bonus（公开接口）

```typescript
const woo = await auth.getWooBonus() // 默认当前登录 userInfoId
// woo.bonus_percent, woo.max_staked_woo, woo.matched_wallet
```


### 字段速查：其它常用响应

#### `CreditChargeItem` / `getCreditCharges`

| 字段 | 类型 | 说明 |
|------|------|------|
| `amount` | number | 扣费 Credits |
| `api_type` | string | 计费 API 类别 |
| `balance_after` | number | 扣费后余额 |
| `description` | string | 描述 |
| `created_at` | string | ISO8601 |
| `machine_ipv6` | string | 机器 IPv6 |
| `call_type` / `agent_id` | string? | 可选调用元数据 |
| `pagination.has_more` | boolean | 是否还有下一页 |

#### `CreditTopupItem` / `getCreditTopups`

| 字段 | 类型 | 说明 |
|------|------|------|
| `amount` | number | 充值金额 |
| `chain` | string | 链 / 渠道（含 stripe） |
| `tx_hash` | string | 交易哈希 |
| `balance_after` | number | 入账后余额 |
| `created_at` | string | ISO8601 |

#### `CreditTxStatus` / `getCreditTxStatus`

| 字段 | 类型 | 说明 |
|------|------|------|
| `credited` | boolean | 是否已入账 |
| `pending` | boolean | 是否处理中 |
| `status` | `'not_detected'?` | 未检测到链上 tx |
| `balance_after` | number? | 入账后余额 |
| `amount` / `chain` / `tx_hash` | optional | 检测到后的详情 |
| `container_id` | string? | 空字符串表示无容器、进 pending |

#### `RedeemGiftCardResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 礼品卡码 |
| `amount` | number | 到账 Credits |
| `credited_to` | `'machine' \| 'pending'` | 入账目标 |
| `new_balance` / `pending_credit` | number \| null | 对应余额 |

#### `PointsExchangeBalance` / `PointsExchangeResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `available_points` | number | 可兑换积分 |
| `exchange_rate` | string | 汇率文案 |
| `points_spent` | number | 本次消耗积分 |
| `credits_received` | number | 本次获得 Credits |
| `new_credit_balance` | number | 兑换后余额 |
| `idempotent` | boolean? | 幂等重放 |

#### `KycStatus` / `KycVerifyResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `verified` | boolean | 是否已 KYC |
| `exempt` | boolean | 是否豁免 |
| `exchanged_credits` / `threshold_credits` | number | 已兑 / 阈值 |
| `card_last4` / `card_brand` | string | 验卡结果 |

#### `ReferralStatus` / `ReferralInviteesResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `my_referral_code` | string \| null | 自己的邀请码 |
| `can_bind` | boolean | 是否还能绑邀请人 |
| `invitee_count` | number | 邀请人数 |
| `total_bonus_earned` | number | 累计 referral bonus |

#### `MigrationRewardClaimResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `amount` | number | 奖励 Credits |
| `credited_to` | `'machine' \| 'pending' \| 'none'` | 入账位置 |
| `already_claimed` | boolean | 是否已领过 |
| `message` | string | 状态说明 |

#### `WooBonusResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `bonus_percent` | number | 额外 credit 百分比 |
| `max_staked_woo` | number | 最高质押 WOO |
| `matched_wallet` | string | 命中档位的钱包 |
| `wallets_checked[]` | `{ wallet, staked_woo }` | 检查明细 |

> 完整 TypeScript 定义与字段 JSDoc 见 SDK：`starchild-auth-sdk/src/types.ts`（构建后 `dist/index.d.ts`）。

### Scope 不足时

服务端返回 **403**，body 类似：

```json
{ "detail": "Insufficient scope: credit:read or credit:write is required." }
```

写接口缺 `credit:write` 时：

```json
{ "detail": "Insufficient scope: credit:write is required for this operation." }
```

集成方应引导用户重新 `login()` 并申请完整 credit scopes，或在 OAuth App 控制台勾选后重新授权。

---
## 场景九：消息排队与注入（Agent 运行中发送新消息）

当 Agent 正在处理消息时（SSE 流未结束），用户可能发送新消息。这时不能直接调用 `/chat/stream`，而是将消息加入**排队队列**。

### 前端实现模式（参考 starchild-web）

```typescript
// 1. 检查 Agent 是否正在运行
const isAgentActive = isStreaming || !!agentBackgroundRunning[threadId]

if (isAgentActive) {
  // 2. 消息加入本地队列（不立即发送到后端）
  const queuedId = `queued-${Date.now()}`
  dispatch(addToMessageQueue({
    threadId,
    message: {
      id: queuedId,
      content: message,
      images: images,      // 可选：base64 图片
      files: files,        // 可选：已上传文件引用
      quote: quoteOptions, // 可选：引用的消息
      status: 'pending',   // pending → sending → sent
      createdAt: Date.now(),
    },
  }))

  // 3. 显示 "当前消息已排队，Agent 完成后自动发送" 提示
  dispatch(updateQueuedMessageStatus({ threadId, messageId: queuedId, status: 'sending' }))

  // 4. 后端在 /chat/stream 完成后，检查 messageQueue
  //    取出 FIFO 的第一条，调用下一个 /chat/stream
} else {
  // Agent 空闲，直接发送
  await sendToChatStream(message, images, files)
}
```

### /chat/stream 请求体格式（完整）

```json
{
  "message": "Hello, analyze this data",
  "thread_id": "thread-uuid",
  "channel": "web",
  "message_id": "queued-1234567890",
  "model": "claude-3-5-sonnet-20241022",
  "images": [
    {
      "base64_data": "...",
      "media_type": "image/png"
    }
  ],
  "files": [
    {
      "name": "data.csv",
      "workspace_path": "/workspace/data.csv",
      "mime_type": "text/csv",
      "size": 1024
    }
  ],
  "quote": {
    "source_message_id": "msg-abc123",
    "quoted_text": "The original message text...",
    "source_role": "user"
  }
}
```

### /chat/stream 响应流程

```
POST /chat/stream → SSE 连接建立
  ← event: agent_start    { session_key: "sess-xxx" }
  ← event: text_delta     { text: "I'll analyze..." }
  ← event: tool_use       { tool_name: "read_file", tool_input: {...} }
  ← event: tool_output    { tool_output: "file content..." }
  ← event: text_delta     { text: "Based on the data..." }
  ← event: agent_end      { stop_reason: "end_turn" }
SSE 连接关闭
→ 后端检查 messageQueue[threadId]
→ 如果有排队消息 → 自动开始下一个 /chat/stream
```

### SSE 事件类型详解

| 事件 | 含义 | payload 示例 |
|------|------|-------------|
| `agent_start` | Agent 开始处理，返回 session_key 用于重连 | `{session_key: "sess-abc123"}` |
| `text_delta` | 增量文本输出（逐 token） | `{text: "Hello"}` |
| `tool_use` | Agent 调用工具 | `{tool_name: "read_file", tool_input: {path: "/a.txt"}}` |
| `tool_output` | 工具返回结果 | `{tool_output: "file contents..."}` |
| `agent_end` | Agent 完成一轮对话 | `{stop_reason: "end_turn" \| "tool_use"}` |
| `error` | 流错误 | `{message: "Error description"}` |
| `agent:interrupted` | Agent 被中断（用户取消/超时） | `{reason: "..."}` |

### /chat/runs/cancel 取消运行

```typescript
// POST /chat/runs/cancel?thread_id=xxx
await auth.cancelRun(threadId)
// 这会中断当前正在运行的 SSE 流
// SSE 连接会收到 agent_end 或 agent:interrupted 事件后关闭
```

### /chat/stream/reconnect 断线重连

当 SSE 连接意外断开（网络问题、页面切换），用 `session_key` 重连：

```typescript
// POST /chat/stream/reconnect?session_key=sess-xxx&channel=web
const stream = await auth.reconnectStream(sessionKey)

// reconnect 返回的 SSE 事件格式相同
// 它会从中断点继续推送剩余的事件
// 如果 Agent 已完成，会立即收到 agent_end
```

---

## 场景十：Agent 集成（直接 token 注入）

Agent 可以在没有浏览器 popup 的情况下使用 SDK：

```typescript
import { StarchildAuth } from 'starchild-auth-sdk'

// Agent 从环境变量或 OAuth 回调获取 token
const accessToken = process.env.STARCHILD_TOKEN!

const auth = new StarchildAuth({
  clientId: process.env.CLIENT_ID!,
  scope: 'profile chat',
  autoLogin: false,  // 不弹出浏览器窗口
  onLogin: () => {},
})

// 注入 token（绕过 popup 流程）
;(auth as any)._accessToken = accessToken

// 现在可以调用所有方法
const threads = await auth.listThreads()
const message = await auth.sendMessage('Summarize my threads')
```

---

## 错误处理

### 登录 popup

```typescript
try {
  await auth.login()
} catch (err: any) {
  if (err.message?.includes('cancelled')) {
    // 用户关闭了弹窗
  } else if (err.message?.includes('blocked')) {
    // 浏览器拦截了弹窗 — 必须在用户点击事件中调用 login()
  }
}
```

### JSON API：`StarchildAuthError`

`getCredits` / `listThreads` / wallet / credit 等 JSON helper 在非 2xx 时 **throw** `StarchildAuthError`（已从 `starchild-auth-sdk` 导出）：

```typescript
import { StarchildAuth, StarchildAuthError } from 'starchild-auth-sdk'

try {
  await auth.credit.getBalance()
} catch (e) {
  if (e instanceof StarchildAuthError) {
    // e.status / e.code / e.detail / e.path / e.insufficientScope / e.response
    if (e.insufficientScope) {
      // 引导重新 login() 申请完整 scopes，或检查 OAuth App 审核 scope
      await auth.login()
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| `status` | HTTP 状态；无响应时为 `0` |
| `code` | 可选机器码 |
| `detail` | 原始 body / detail |
| `path` | 请求路径 |
| `insufficientScope` | OAuth scope 不足类 403 的启发式标记 |
| `response` | 原始 `Response`（若有） |

### SSE / 原始 Response

`sendMessage` / `reconnectStream` 仍返回原始 `Response`，需自行检查 `ok`：

```typescript
const stream = await auth.sendMessage('hello')
// 或 auth.chat.send('hello')
if (!stream.ok) {
  const error = await stream.json()
  console.error('API error:', error.detail)
  if (stream.status === 401) {
    // token 过期 — SDK 会尝试自动刷新；仍失败则 onTokenRefreshFailed
  } else if (stream.status === 403) {
    // 权限不足 — scope 不满足
  }
}
```

---

## 快速参考：所有 API 端点

| 分类 | 端点 | 方法 | Scope |
|------|------|:--:|:-----:|
| **Auth** | `/v1/oauth/userinfo` | GET | profile |
| | `/v1/private/oauth/authorize` | POST | — (go-api) |
| | `/v1/oauth/refresh` | POST | — (go-api) |
| | `/v1/oauth/logout` | POST | — (go-api) |
| **Bind (SDK)** | `auth.bindAccount()` → 主站 `/?account_tab=linked-accounts` | — | profile |
| | `auth.getBindAccountUrl()` / `auth.isGuest()` | — | profile |
| **Token (SDK)** | `getToken()` / `getRefreshToken()` / `refreshToken()` | — | — |
| **Namespace** | `auth.profile` / `chat` / `threads` / `messages` / `containers` / `skills` / `media` / `shares` / `feedback` / `jobs` / `wallet` / `credit` | — | 同 flat |
| **Chat** | `/chat/stream` | POST | chat |
| | `/chat/stream/reconnect` | POST | chat |
| | `/chat/runs/cancel` | POST | chat |
| | `/chat/model` | GET/POST | chat |
| **Threads** | `/api/clawd/threads` | GET/POST | chat |
| | `/api/clawd/threads/{id}` | GET/DELETE | chat |
| | `/api/clawd/threads/search` | GET | chat |
| | `/api/clawd/threads/{id}/pin` | POST | chat |
| | `/api/clawd/threads/{id}/title` | POST | chat |
| **Messages** | `/api/clawd/messages` | GET/DELETE | chat |
| **Containers** | `/api/cloud/containers` | GET | chat |
| | `/api/cloud/containers/deploy` | POST | chat |
| | `/api/cloud/containers/start` | POST | chat |
| | `/api/cloud/containers/stop` | POST | chat |
| | `/api/cloud/containers/restart` | POST | chat |
| | `/api/cloud/containers/wake` | POST | chat |
| | `/api/cloud/containers/rename` | PUT | chat |
| | `/api/cloud/containers/status` | GET | chat |
| | `/api/cloud/containers/metrics` | GET | chat |
| | `/api/cloud/containers/compute-config` | POST | chat |
| | `/api/cloud/containers/{id}/update` | POST | chat |
| **Skills** | `/api/skills/catalog` | GET | chat |
| | `/api/skills/catalog/search` | GET | chat |
| | `/api/skills/catalog/{source}/{name}` | GET | chat |
| **Media** | `/api/clawd/images/upload` | POST | chat |
| | `/api/audio/transcribe` | POST | chat |
| | `/v1/synthesize` | POST | chat |
| **Shares** | `/api/clawd/shares` | GET/POST | chat |
| | `/api/clawd/shares/{id}` | GET/DELETE | chat |
| | `/api/clawd/shares/{id}/fork` | POST | chat |
| **Feedback** | `/api/clawd/feedback` | PUT/DELETE | chat |
| **Jobs** | `/scheduled-jobs` | GET/POST | chat |
| **Wallet** | `/api/cloud/containers/portfolio/evm` | GET | chat |
| | `/api/cloud/containers/wallets` | GET | chat |
| | `/api/cloud/containers/wallet` | POST/DELETE | chat |
| | `/wallet/export` | POST | chat |
| **Billing** | `/coinbase/onramp-session` | POST | chat |
| **WebSocket** | `/ws/sync` | WS | chat |
| | `/ws/terminal/{id}` | WS | chat |
| | `/ws/metrics` | WS | chat |
| **Notifications** | `/v1/agentx/notifications` | GET/POST | chat |
| | `/v1/agentx/notifications/unread-count` | GET | chat |
| **Models** | `/chat/models` | GET | chat |
| **Free quota** | `/v1/free-quota` | GET | chat |
| **Credits balance** | `GET {creditApiBase}/api/credits` | GET | credit:read |
| **Credits charges** | `GET .../api/charges` | GET | credit:read |
| **Credits topups** | `GET .../api/topups` | GET | credit:read |
| **Credits usage** | `GET .../api/usage/daily` | GET | credit:read |
| **Credits pending** | `GET .../api/pending` | GET | credit:read |
| **Credits tx** | `GET .../api/tx/{hash}` | GET | credit:read |
| **Stripe session** | `POST .../api/stripe/create-session` | POST | credit:write |
| **Gift redeem** | `POST .../api/gift-cards/redeem` | POST | credit:write |
| **Points balance** | `GET .../api/points/balance` | GET | credit:read |
| **Points exchange** | `POST .../api/points/exchange` | POST | credit:write |
| **KYC** | `GET/POST .../api/kyc/*` | * | read/write |
| **Referral** | `GET/POST .../api/referral/*` | * | read/write |
| **Migration reward** | `GET/POST .../api/migration/reward/*` | * | read/write |
| **WOO bonus** | `GET .../api/public/users/{id}/woo-bonus` | GET | public |

---

## 本地测试指南（Agent 必读）

> **给 Agent 的执行原则**：OAuth `login()` 必须在**真实浏览器页面**里测（需要 popup + 用户手势 + 页面 Origin）。拿到 token 后，API 可用 curl/Node 脚本测。禁止假设「纯 Node 无 Origin 能跑通 popup 登录」。

### 1. 两套 Origin，不要混

| 角色 | Origin 示例 | 谁配置 |
|------|-------------|--------|
| **主站 web（授权 popup）** | `http://localhost:6066` **与** `https://localhost:6066` | 服务端**静态 CORS** 已统一放行（go-api `CORS_ORIGINS` / ai-agent `CORS_ALLOWED_ORIGINS` / clawd `CORS_ORIGINS`；生产 env 也应包含这两项） |
| **第三方应用页（集成 SDK 的站点）** | 如 `http://localhost:3333`、`http://localhost:5173` | 必须写进该 OAuth App 的 **`allowed_origins`**（注册/审核时填写；与页面地址栏 **完全一致**，含 scheme 与端口） |

- Popup 打开的是主站（本地 web 或 `https://iamstarchild.com`），浏览器 `Origin` 是主站。
- SDK 跑在第三方页，API 请求的 `Origin` 是第三方 origin → 靠 OAuth client 动态合并进 CORS。
- `authorize` 时：Header Origin = 主站（trusted web），body `origin` = 第三方 origin（校验 client 白名单）。

### 2. 生产默认 Base URL（SDK 0.4.x）

与 starchild-web 对齐，**默认即线上**，本地 demo 一般不用改：

| 配置项 | 默认 |
|--------|------|
| `origin` | `https://iamstarchild.com`（popup 主站） |
| `apiBase` | `https://go-api.iamstarchild.com/v1` |
| `chatApiBase` | `https://ai-api.iamstarchild.com` |
| `clawdApiBase` | `https://preview.iamstarchild.com`（HTTP chat/stream、jobs） |
| `clawdWsBase` | `wss://preview.iamstarchild.com`（WS） |
| `creditApiBase` | `https://credit.iamstarchild.com` |

本地联调**全套后端**时，再显式改成 `http://127.0.0.1:8000/v1`、`http://127.0.0.1:8008`、`http://127.0.0.1:8009` 等（见仓库 clinerules 端口表）。

### 3. 场景 A — 第三方本地页 + 线上 API（最常见）

**目标**：在 `http://localhost:<port>` 跑集成方页面，登录与 API 打生产。

1. OAuth App `allowed_origins` 包含页面 Origin（例 `http://localhost:3333`），status=approved，scopes 够用。
2. 页面用 SDK：`clientId` + 需要的 `scope`；**不要**把第三方 origin 配成 6066。
3. 用浏览器打开第三方页 → 用户点击 → `auth.login()` → popup 走 **线上** `https://iamstarchild.com`（默认 `origin`）。
4. 登录成功后在同一页面调 `auth.chat` / `auth.credit` / SSE / WS。
5. 若 CORS 失败：检查第三方 origin 是否在 client 白名单；生产 go-api/ai-agent/clawd 的静态 CORS 是否含主站相关域名（本地 web 测 popup 时才需要 6066）。

**仓库内参考**：
- SDK demo：`starchild-auth-sdk/example/index.html`、`test-sdk-full.html`（默认生产 URL）
- Orderly 示例：`orderly-test-dex` + `starchild-orderly-plugin`

### 4. 场景 B — 本地主站 web（6066）+ 本地或线上 API

**目标**：改 starchild-web / 测 authorize 中介、Guest 绑定等。

1. 启动 starchild-web：默认 **`http://localhost:6066`**（也可用 https 本地证书 → `https://localhost:6066`）。
2. 确认 API 侧静态 CORS 含：
   - `http://localhost:6066`
   - `https://localhost:6066`
   - （可选）`https://starchild.dev:6066`
3. Env 名：
   - go-api：`CORS_ORIGINS`（设置后**整表替换**代码默认，须同时保留线上域名 + 上述 6066）
   - ai-agent：`CORS_ALLOWED_ORIGINS`（同上）
   - clawd：`CORS_ORIGINS`（entrypoint 默认已含 6066 http/https）
4. 第三方仍用自己的 origin 注册；本地 web 只负责 popup/中介。

### 5. 场景 C — 浏览器 vs Node/脚本

| 步骤 | 浏览器 | curl / Node |
|------|--------|-------------|
| `login()` popup | 必须 | **不能**（无窗口、无真实页面 Origin） |
| 持 token 调 userinfo / threads / credits | 可以 | 可以（`Authorization: Bearer`） |
| 自动带 CORS | 浏览器执行 | 脚本无 CORS；直连即可 |
| 测 CORS 是否放行 | DevTools / 页面请求 | `OPTIONS` + `Origin` 头模拟 preflight |

**Agent 推荐流程**：
1. 浏览器完成登录，从 `onLogin` / DevTools / `auth.getToken()` 取 access token（refresh 仅调试用 `getRefreshToken()`，勿外传）。
2. 再用 curl 跑矩阵（scope 门闸、403、credits 等）。
3. 需要回归 popup/CORS 时，再用 Playwright/真实页面，**页面 URL 的 origin 必须已在 client 白名单**。

### 6. CORS 预检（Agent 可直接跑）

```bash
# 期望：ACAO 回显同一 Origin（静态主站 web）
curl -s -D - -o /dev/null -X OPTIONS 'https://go-api.iamstarchild.com/v1/oauth/refresh' \
  -H 'Origin: http://localhost:6066' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization,content-type' \
  | tr -d '\r' | grep -i access-control-allow-origin

curl -s -D - -o /dev/null -X OPTIONS 'https://go-api.iamstarchild.com/v1/oauth/refresh' \
  -H 'Origin: https://localhost:6066' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization,content-type' \
  | tr -d '\r' | grep -i access-control-allow-origin

# 第三方本地 origin（须已在该 OAuth client allowed_origins，且 client approved）
curl -s -D - -o /dev/null -X OPTIONS 'https://go-api.iamstarchild.com/v1/oauth/refresh' \
  -H 'Origin: http://localhost:3333' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization,content-type' \
  | tr -d '\r' | grep -i access-control-allow-origin

# 期望：无 ACAO（拒绝）
curl -s -D - -o /dev/null -X OPTIONS 'https://go-api.iamstarchild.com/v1/oauth/refresh' \
  -H 'Origin: https://evil.example.com' \
  -H 'Access-Control-Request-Method: POST' \
  | tr -d '\r' | grep -i access-control-allow-origin || echo 'DENY_OK'
```

本地后端把 host 换成 `http://127.0.0.1:8000` / `:8008` / `:8009` 即可。

### 7. 登录后 API 冒烟（有 token 后）

```bash
TOKEN='<access_token from browser login>'
# profile
curl -s -H "Authorization: Bearer $TOKEN" https://ai-api.iamstarchild.com/v1/oauth/userinfo
# chat（无 chat scope 应 403）
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
  https://ai-api.iamstarchild.com/api/clawd/threads
# credits（需 credit:read）
curl -s -H "Authorization: Bearer $TOKEN" https://credit.iamstarchild.com/api/credits
```

### 8. 本地全栈端口（仓库开发）

| 服务 | 端口 |
|------|------|
| starchild-web | `http://localhost:6066` |
| go-api | `http://127.0.0.1:8000` |
| ai-agent | `http://127.0.0.1:8008` |
| clawd | `http://127.0.0.1:8009` |
| credit-api | 按 transparent-proxy 部署（生产 `credit.iamstarchild.com`） |

动态 CORS：go-api / ai-agent / clawd 会定期拉取 **approved + active** OAuth client 的 `allowed_origins` 合并进白名单（默认约 5 分钟；改 origin 后若未生效可重启服务或等刷新）。

### 9. 安全注意（测试时）

- 静态放行仅限精确 `http://localhost:6066` 与 `https://localhost:6066`，不是任意 localhost 端口。
- 第三方每个端口/scheme 都要单独进 `allowed_origins`。
- 不要把 refresh token 写进日志、issue、或发给用户聊天。
- 生产 env 覆盖 CORS 时必须**整表**包含线上域名 + 需要的本地 web origin，避免只配 localhost 导致主站跨域全挂。

### 10. Agent 检查清单（测 SDK / OAuth 前勾选）

- [ ] OAuth client `allowed_origins` **精确等于**第三方测试页 Origin
- [ ] client `status=approved` 且 `is_active`，scopes 含要测的能力
- [ ] `login()` 在浏览器 click 路径调用
- [ ] 主站本地 popup 时，API CORS 含 `http://localhost:6066` 与 `https://localhost:6066`
- [ ] SDK base URL：打生产用默认；打本地后端再改 apiBase/chatApiBase/clawd*
- [ ] CORS 失败先分清是「静态主站 origin」还是「OAuth 第三方 origin」
- [ ] scope 矩阵：profile-only 不能 threads；credit:read 不能 write
- [ ] 脚本测试只在**已有 token** 后进行

---

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 弹窗被拦截 | 浏览器要求用户手势触发 | 确保 `login()` 在 click handler 中调用 |
| Origin 不匹配 | Allowed Origin 配置不符 | 检查 OAuth Apps 的 origin 与**第三方页面**完全一致（含 http/https 与端口） |
| 本地 web popup CORS | 6066 未进静态 CORS | 确认 go-api/ai-agent/clawd（及生产 env）含 `http://localhost:6066` 与 `https://localhost:6066` |
| 第三方本地 CORS | origin 未进 client 或不在动态列表 | 写入 `allowed_origins` 并 approved；等 CORS 刷新或重启 API |
| Node 脚本无法 login | popup 依赖浏览器 | 浏览器登录取 token 后再用脚本调 API |
| `onLogin` 不触发 | 用户未确认授权或 popup 被关闭 | 检查 `onAuthCancelled` 和 `onAuthError` |
| SSE 流中断 | 网络波动或容器重启 | 用 `session_key` 调用 `reconnectStream()` |
| WS 断开 | 连接超时或服务器重启 | 实现指数退避自动重连 |
| 403 on container delete | OAuth token 不允许删除容器 | 这是预期行为，无法绕过 |
| 401 after token refresh | refresh token 过期 | 引导用户重新 login() |
| Guest 需绑定正式账号 | `userInfo.isGuest === true` | 调用 `auth.bindAccount()` 跳转主站 Linked accounts，勿自建 `/guest/bind`；Guest 登录本身走 `login()` 主站 popup，无 `loginAsGuest` |
| 需要 refresh token | 自建刷新或调试 | 用 `getRefreshToken()`；优先 SDK `refreshToken()`；勿日志/外传 |
| JSON API throw | 非 2xx | catch `StarchildAuthError`，看 `insufficientScope` |
| 403 Insufficient scope credit:* | token 未含 credit scope | 重新 login 并请求 `credit:read`/`credit:write`；检查 OAuth App 是否已审核通过 |
| Credits 调不通 / CORS | origin 未在 client allowed origins | 与 chat 相同，origin 必须在 OAuth client 白名单 |
| Stripe 成功但余额未变 | 仍在 pending 或 tx 未 credited | 轮询 `getCreditTxStatus` / `getPendingCredit` / `getCredits` |

# para CLI —— 行为说明

完整语法可通过 `para --help` 和 `para <command> --help` 查看。本文件覆盖 `--help` 未涉及的内容：护栏、坑点，以及 CLI 在整个 Para 集成工作流中的位置。

CLI 本身的权威来源：https://docs.getpara.com/v2/cli/commands

## 安装与认证 —— 永远不要替用户做这些事

- **不要替用户安装 CLI。** 命令是 `npm install -g @getpara/cli`（或 `pnpm add -g @getpara/cli`，或者用 `npx @getpara/cli@latest <command>` 不安装直接运行）—— 告诉他们，不要替他们执行。
- **不要替用户运行 `para login`。** 它会打开浏览器标签页执行 OAuth（带 PKCE），只有用户本人能完成。凭证会落到 `~/.config/para/credentials.json`（文件权限 0600）。无头环境下可以用 `para login --no-browser`，但 monskills 面向交互式使用 —— 把命令呈现给用户并等待。
- **`para auth status` 是判断会话是否有效的权威方式。** 退出 0 = 会话有效。需要程序化判断登录状态时用它，而不是 `para whoami`，因为 `whoami` 只读本地上下文，而 `auth status` 会回服务器校验。monskills 的 hook 通过 `auth status` 拦截 `para` 命令。
- **`para whoami` 用于向用户展示当前上下文**（组织、项目、环境、过期时间）。当用户问 “我现在用哪个账号登录” 或在执行破坏性操作前确认当前上下文时使用它。

## 配置解析顺序

Para 按以下优先级解析配置（高在前）：

1. CLI flag（`--project-id`、`--env` 等）
2. 环境变量（`PARA_ENVIRONMENT`、`PARA_ORG_ID`、`PARA_PROJECT_ID`）
3. 项目配置（当前目录的 `.pararc`）
4. 全局配置（`~/.config/para/config.json`）
5. 内置默认值

当某条命令操作 “当前项目” 时，会沿这条链解析。如果用户在带 `.pararc` 的目录中执行 `para`，该 pin 会胜过全局默认 —— 对多 Para 项目的 monorepo 很方便，但用户如果没意识到自己 `cd` 到了某个子目录，就容易混淆。

`para config get` 会显示已解析的值，以及它来自哪里。当行为与预期不符时优先使用它。

## `para init` —— 为团队 pin 住项目

```bash
para init                # 交互式
para init --no-input     # 非交互（任何沙盒 / 无头环境都用这个）
para init --force        # 覆盖已存在的 .pararc
```

在当前目录创建 `.pararc`，pin 住组织 + 项目 + 环境。提交它 —— 这样队友无需手动切换就能落到同一个 Para 上下文。文件中不含密钥。

**无头 / 沙盒终端 —— 使用 `--no-input`。** 没有真正的 TTY 时，`para init` 会以 `TTY initialization failed: uv_tty_init returned EINVAL` 中止。这会出现在 Codespaces、大多数 CI runner，以及任何包裹 shell 但不转发 PTY 的 agent 中。`--no-input` 会跳过交互提问，并使用全局配置里的当前组织 / 项目 / 环境 —— 在此之前请通过 `para projects switch` 与 `para config set defaultEnvironment <beta|prod>` 先 pin 好。

如果用户在父目录已经有一个 `.pararc`，又在子目录运行 `para init`，就会出现两个 pin —— 离当前目录最近的胜出。避免这种情况：只在前端 `package.json` 同级目录运行一次 `para init`。

## `para create` 是有意排除的

本 skill 永远不会脚手架一个全新的应用。项目脚手架由 `scaffold/` skill 负责，它产出供你集成 Para 的 Next.js 前端。不要运行 `para create` —— 它会生成一个平行的应用，搞乱工作流。如果用户需要全新脚手架，引导他们去 `scaffold/` skill，再回来用本 skill 把 Para 接进它生成的项目。

## `para doctor` —— 诊断，每次改动接线后都跑

```bash
para doctor                    # 人类可读
para doctor --json             # 机器可读，有错误时退出 1（适合 CI）
para doctor --category setup   # 仅一个分类
para doctor --severity error   # 仅阻塞性问题
```

分类：`configuration`、`dependencies`、`setup`、`best-practices`。严重级别：`error`、`warning`、`info`。

它会检查：

- API Key 环境变量是否存在并使用了正确前缀（Next.js 用 `NEXT_PUBLIC_`，Vite 用 `VITE_`）。
- 是否导入了 Para 的 CSS。
- `ParaProvider` 是否包裹了应用。
- 是否设置了 `QueryClient`（Para 的 React hooks 需要 React Query）。
- 使用 Para hooks 的 Next.js 组件是否带有 `"use client"` 指令。
- 所有 `@getpara/*` 包是否在同一个小版本号上。
- 必要的链相关依赖是否安装（例如 EVM 需要 `viem`、`wagmi`）。
- 是否仍在 import 已弃用的 `@getpara/*` 包。

每次集成步骤之后、每次依赖升级之后都跑一次 `para doctor`。加 `--json` 后可以安全地从脚本调用 —— 退出 1 即代表有需要修复的问题。

## API Key 管理

- `para keys list` —— 列出 Key（值已脱敏）。
- `para keys get` —— 默认返回当前项目当前环境的 Key。`--show-secret` 打印密钥；`--copy-secret` 复制密钥。**绝不要在 `--show-secret` 后把值回显到回复中。**
- `para keys create -n <internal-name> --display-name <user-facing-name>` —— 在当前项目里创建新 Key。
- `para keys rotate` —— 默认轮换公钥。`--secret` 轮换密钥。旧 Key 立刻被禁用，所以同一改动中要更新前端环境变量。
- `para keys archive` —— 吊销一个 Key。CLI 端不可逆；用户必须去 Dashboard 反归档。

轮换或归档之后，更新前端的环境变量文件并重新部署。不要把新值打回给用户 —— 自己把它写进 env 文件，然后用一句 “已轮换并更新 `.env.local`” 确认。

## `para keys config` —— 安全、品牌、Ramps、Webhook

`para keys config show [category]` 展示当前设置。`--json` 返回脚本可解析的输出。五个分类：

| 分类 | 控制的内容 |
|---|---|
| `security` | **二次验证方式**（PASSKEY/PASSWORD/PIN）、允许的 origin、会话时长（5–43200 分钟）、交易弹窗、IP 白名单（CIDR） |
| `branding` | 前景色 / 背景色 / 强调色、字体、社交 URL、欢迎邮件 / 备份套件邮件 |
| `setup` | 钱包类型、Cosmos 前缀、Apple Team ID、iOS Bundle ID、Android 包名 + 指纹 |
| `ramps` | 买 / 收 / 提的开关、提供商顺序（RAMP/STRIPE/MOONPAY）、默认金额 |
| `webhooks` | 端点 URL、订阅的事件、开关、测试发送、密钥轮换 |

这些大多也可以在开发者后台里编辑 —— 用用户偏好的方式即可。CLI 更适合重复编辑或脚本化设置。

**`security` 控制的不是登录弹窗里出现哪些 IDP 按钮。** 这里的 `PASSKEY/PASSWORD/PIN` 是 Para 提供给用户做*恢复*的**二次验证方式** —— 不是登录页上的 OAuth 提供商按钮（Google、Apple、Twitter 等）。要隐藏社交登录或手机号登录，请编辑 `ParaProvider` 上的 `paraModalConfig`（客户端）；详见 `para-workflows.zh.md` → “客户端 vs Key 端 —— 各自控制什么”。

### IP 白名单坑点

在 Para 项目的 `security` 配置里启用 IP 白名单时，如果没先把用户自己的 IP 加进去，他们（以及他们部署到线上的 origin）会被自己锁在外面。CLI 不会自动检测 “当前 IP” —— 由用户提供。正确顺序：

1. 拿到用户当前 IP（让他们告诉你，或运行 `curl -s https://api.ipify.org`）。
2. 通过 `para keys config`（security 分类）加入白名单。
3. 加入所有后端 / Serverless 的 IP。
4. **然后**才开启强制。

## 组织 / 项目切换

- `para orgs list` / `para orgs switch [<id>]` —— 不传 id 时进入交互选择。
- `para projects list` / `para projects switch [<id>]` —— 同上。
- `para projects create -n <name> --framework nextjs|vite|react-native|...` —— 不打开 Dashboard 直接从 CLI 创建。
- `para projects archive` 可通过 `para projects restore` 反归档。`para keys archive` 从 CLI 端**不可**反归档。

## 环境：beta vs prod

Para 有两个环境：`beta`（默认，用于开发 / 测试）与 `prod`。它们有独立的 API Key。用 `para config set defaultEnvironment <beta|prod>`（全局）或 `para config set --local defaultEnvironment <env>`（写入 `.pararc`）切换。

本地开发与 PR Preview 用 `beta`；只有当认证方式、品牌与 Webhook 都在 beta 验证过之后再切到 `prod`。混用 beta 与 prod Key（例如把 beta Key 放进生产前端）会悄无声息地把用户路由到错误的项目 —— `para doctor` **抓不到**这种情况，必须自行核对。

## 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 用户错误（参数错误、未登录、未知项目，或 `para doctor --json` 发现错误） |
| `2` | API / 服务端错误 |

不要只依赖 stdout 内容 —— 一定要检查退出码。`para doctor --json` 在存在问题时退出 1 是*正确*行为，意味着诊断成功跑完并发现了问题。

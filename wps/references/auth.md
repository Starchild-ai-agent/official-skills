# 认证详情与故障排除

> 何时打开：`auth login` 失败需手动获取 Token / 需要诊断认证状态 / 需要退出登录。日常使用无需阅读。

## 诊断与退出

| 操作 | 命令 |
|------|------|
| 查看状态 | `kdocs-cli auth status` |
| 退出登录 | `kdocs-cli auth logout` |

## 手动获取 Token（login 失败时的兜底方案）

当 `kdocs-cli auth login` 因环境问题执行失败时，引导用户手动获取：

1. 打开 **WPS 云文档** 微信小程序 → **我** → **龙虾专属入口** → 复制 Token
2. 用户将 Token 提供给 Agent
3. Agent 保存到密钥链：`kdocs-cli auth set-token "<TOKEN>"`

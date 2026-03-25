# ⛓️ Starchild Official-Skills Crypto 体验优化计划

**日期:** 2025-03-25
**目标:** 小模型也能在 Crypto 场景下达到良好效果
**周期:** 7 天出成果

---

## 一、诊断数据摘要

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| SKILL.md 小模型可解析分 | 平均 49/100 | ≥70/100 |
| 工具失败后模型能理解错误 | 0/150 (全黑洞) | ≥90% |
| 带金融操作的 skill 有安全检查 | 2/8 | 8/8 |
| 返回 None 的 except 块 | 62 处 | 0 |
| print() 替代结构化错误 | 88 处 | 0 |
| Crypto skill 文档有单位说明 | 1/12 | 12/12 |

### 核心发现

**小模型失败的三大原因（按影响力排序）：**

1. **150 个错误黑洞** — 62 处 silent `return None` + 88 处 `print()` 到 stderr
   - 模型收到 None，无法判断是"没有数据"还是"调用失败"
   - 大模型靠推理能力猜到出错了，小模型直接给用户说"没有结果"

2. **SKILL.md 缺少 Quick Reference** — 26/27 skill 没有
   - 小模型上下文窗口有限，长文档读到一半就丢掉了
   - 最影响的：coinglass(37个tool)、debank(34个tool)、coingecko(29个tool)

3. **金融参数无单位规范** — amount/size/value 含义模糊
   - hyperliquid: `size` 是 USD 计价还是 coin 计价？
   - 1inch: `amount` 是 raw token 还是 human-readable？
   - 小模型没有常识兜底，经常搞错数量级

---

## 二、7 天交付计划

### Day 1-2: 🔴 Error Black Hole 消灭 (最高优先级)

**做什么：** `shared/errors.py` + 逐 skill 替换

**改之前（小模型体验）：**
```
User: "查一下 BTC 的资金费率"
Tool call: funding_rate(symbol="BTC")
Tool result: None
Small Model: "BTC 目前没有资金费率数据。"  ← 完全错误，其实是 API 超时
```

**改之后：**
```
Tool result: {"ok": false, "error": "API_TIMEOUT", "message": "CoinGlass API 超时(30s)", "suggestion": "重试一次，或检查是否传了正确的 symbol(应为 BTC 不是 bitcoin)"}
Small Model: "API 超时了，我重试一下。" ← 正确恢复
```

**具体文件改动：**

| 文件 | 当前问题 | 补丁内容 |
|------|---------|---------|
| `coinglass/*.py` | 76 处 `return None` + 8 处 silent except | 全部替换为 `SkillError` raise |
| `birdeye/*.py` | 15 处 `return None` + 2 处 silent except | 同上 |
| `hyperliquid/client.py` | 3 处 silent except (含签名模块) | 区分 network/auth/validation 错误 |
| `taapi/*.py` | 2 处 `return None` + 1 处 silent except | 同上 |
| 全部 `tools.py` | `except Exception as e` → 用原始 str(e) | 包装为结构化 JSON 错误 |

**产出物：**
- `shared/errors.py` — 错误分类体系 (已写好)
- `shared/response.py` — 统一 ok/fail 格式 (已写好)
- 各 skill 的 `.patch` diff 文件

---

### Day 2-3: 🟡 SKILL.md 小模型适配

**做什么：** 为 12 个含代码 skill 添加 Quick Reference 头部

**改造标准（preview-dev 是标杆，得分 90/100）：**

```markdown
## Quick Reference        ← 小模型只读这段
| Tool | 用途 | 必填参数 |
|------|------|---------|
| hl_order | 下单 | coin, side, size(USD) |
| hl_account | 查仓位 | 无 |

### 参数单位速查
- size: 永远是 USD 金额（不是 coin 数量）
- price: 市场价格，省略 = 市价单
- leverage: 整数，默认 cross margin

### ⚠️ 常见陷阱
- hl_account 只显示 Perp，用 hl_total_balance 查全部余额
- 下单前必须先 hl_total_balance 确认有钱
```

**优先级排序（高频 × 低分 = 先改）：**

| Skill | 当前分 | 工具数 | 优先级 |
|-------|--------|-------|--------|
| coinglass | 20 | 37 | P0 |
| twelvedata | 15 | 10 | P0 |
| coingecko | 30 | 29 | P0 |
| hyperliquid | 40 | 20 | P1 |
| 1inch | 55 | 8 | P1 |
| debank | 45 | 34 | P1 |
| aave | 65 | 5 | P2 |

**产出物：**
- 7 份 SKILL.md 的 Quick Reference 补丁
- SKILL.md 模板标准文档 (已写好)

---

### Day 3-4: 🟡 Crypto Safety Layer

**做什么：** 金融操作的 pre/post 检查中间件

**必须覆盖的场景：**

```
场景 1: 滑点保护
  改前: 1inch swap 无默认滑点 → 小模型忘记设 slippage → 用户被 MEV 攻击
  改后: 默认 1% 滑点，超过 5% 自动拒绝并提示

场景 2: 金额单位验证
  改前: hl_order(size=100) → 100 USD? 100 BTC? 看心情
  改后: 参数名改为 size_usd, 传入 coin 数量自动拒绝

场景 3: 大额操作二次确认
  改前: swap 10000 USDC → 直接执行
  改后: >$1000 操作返回 confirmation_required，等用户确认

场景 4: 链上 finality 教育
  改前: "交易已发送" → 用户以为已成交
  改后: "交易已提交(tx:0x...),预计 2 分钟确认。确认前资金不会到账。"
```

**产出物：**
- `shared/crypto_safety.py` — 安全检查中间件 (已写好)
- 各交易类 skill 的集成补丁

---

### Day 4-5: 🟡 HTTP Retry + 错误恢复

**做什么：** 统一 retry 中间件

**当前问题：** 12 个 skill 中只有 3 个有 retry 逻辑，且实现各不相同

```
coinglass: 无 retry → API 偶发 429 → return None → 小模型："没数据"
birdeye:  无 retry → RPC 超时 → return None → 小模型："代币不存在"  
debank:   无 retry → 502 → 34 个工具全部静默失败
```

**产出物：**
- `shared/retry.py` — 指数退避 + 速率限制 (已写好)
- 集成方案 (1行代码接入)

---

### Day 5-7: 🟢 验证 + 集成测试

详见下方测试方案。

---

## 三、不做的事（及原因）

| 提议 | 不做 | 原因 |
|------|------|------|
| WebSocket 实时监听 | ❌ | 需改平台核心架构，skill 层无法实现 |
| Nonce Manager | ❌ | HL 用 timestamp，EVM 由 Privy 管理 |
| 沙盒隔离 | ❌ | 需要 OS 级方案，Python 做不到 |
| Prompt Injection 防御 | ❌ | 这是 Platform 层安全，不是 skill 层 |
| Permission Manager 弹窗 | ❌ | 已有 Privy Policy Engine 实现 |

---

## 四、成功标准

| 指标 | 测试方法 | Pass 标准 |
|------|---------|----------|
| 错误可理解率 | 模拟 150 种失败，检查返回格式 | 100% 结构化 JSON |
| 小模型文档解析 | Quick Reference 自动评分 | 平均 ≥70/100 |
| 交易安全 | 模拟越界操作(无余额下单等) | 100% 被拦截 |
| Retry 覆盖 | 模拟 429/502/timeout | 100% 自动重试 |
| 端到端工作流 | 5 个 crypto 核心流程模拟 | 小模型也能走通 |

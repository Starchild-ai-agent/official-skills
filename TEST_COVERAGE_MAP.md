# 🗺️ 测试覆盖地图 — 一图看懂

> **读法：** 左边是"补丁模块"（我们写的改进代码），右边是"测试"（验证它能用）。
> 每条线连的就是"这个测试在验证那个功能"。

---

## 总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    4 个补丁模块 (806 行代码)                      │
│                    63 个测试 (全部通过 ✅)                        │
│                    覆盖 5 个场景维度                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 模块 → 测试 对应关系

### 📦 模块 A: errors.py — "出错了该告诉 AI 什么"

**解决什么问题？**
> 原来 skills 出错后返回 `None` 或空字符串，小模型看到后完全不知道发生了什么，
> 也不知道该怎么修。现在错误自带分类码 + 人话建议。

```
errors.py                              test_patches_errors.py (14 tests)
─────────                              ─────────────────────
SkillError (基类)                 ──→  A1: 格式包含 ❌ + 错误码 + 工具名 + 建议
  ├ format()                      ──→  A2: 自动附带上下文 (余额=100, 需要=500)
  │
  ├ TransientError (可重试)       ──→  A3: retryable=True ✓
  │  ├ RateLimitError             ──→  A5: 包含服务名 + 等多久再试
  │  ├ ServiceUnavailableError
  │  └ TimeoutError
  │
  ├ UserInputError (用户的锅)     ──→  A4: retryable=False ✓ (别重试了, 参数不对)
  │  ├ InvalidParameterError
  │  └ UnsupportedAssetError
  │
  └ ChainError (链上问题)
     ├ InsufficientBalanceError   ──→  A6: 自动算缺口 (有100, 要500, 还差400)
     ├ InsufficientGasError       ──→  A7: 自动识别链→原生代币 (ETH/MATIC/SOL)
     ├ TransactionRevertedError   ──→  A9: 带 tx_hash + revert 原因
     ├ SlippageExceededError      ──→  A8: 自动算实际滑点百分比
     └ NonceError
 
  safe_call() 自动分类器          ──→  A10-A14: 把任何 exception 自动归类
```

**关键验证点：**
- ✅ 小模型收到的错误信息自带"下一步该做什么"
- ✅ "可重试 vs 不可重试" 有明确标记，小模型不会盲目重试用户输入错误
- ✅ 链上错误 (余额不足/Gas不足) 自动计算差额，小模型能直接转述给用户

---

### 📦 模块 B: response.py — "成功了该怎么回复"

**解决什么问题？**
> 12 个 skill 有 6 种返回格式 (dict / str / ToolResult / list / None / json_string)，
> 小模型不知道该怎么解析。现在统一用 `ok()` / `fail()`。

```
response.py                            test_patches_response.py (14 tests)
───────────                            ──────────────────────
ok(data, summary)                 ──→  B1-B3: dict/list/scalar 全部标准化
  │  返回: {"status":"ok",             B14: summary 字段直接可读, 不需要解析
  │         "data":{...},          
  │         "summary":"BTC $67,420"}
  │
fail(tool, reason, suggestion)    ──→  B4-B5: 失败也有结构 (code + suggestion)
  │
fmt_price("BTC", 67420, +2.3)    ──→  B6-B8: 自动处理大数逗号/小数精度/涨跌符号
  │  → "BTC: $67,420.00 (+2.30%)"
  │
fmt_balance([...])                ──→  B9-B10: 自动生成 Markdown 表格 + 总计
  │  → | Token | Amount | USD |
  │    |-------|--------|-----|
  │    | ETH   | 1.5    | $5K |
  │    | Total |        | $5K |
  │
fmt_table(data, columns)         ──→  B11-B13: 通用表格, 超50行自动截断
```

**关键验证点：**
- ✅ 不管 skill 返回什么类型 (dict/list/数字/字符串)，小模型都收到统一格式
- ✅ `summary` 字段 = 一句人话总结，小模型最坏情况下只读这一行就够
- ✅ 价格/余额自动格式化成人类可读的 Markdown

---

### 📦 模块 C: retry.py — "网络抖了该怎么办"

**解决什么问题？**
> 10/12 个 skill 没有任何重试逻辑。CoinGlass 返回 502？直接报错。
> 现在自动重试 + 指数退避 + 随机抖动。

```
retry.py                               test_patches_retry.py (12 tests)
────────                               ──────────────────────
RetryConfig                       ──→  C1-C2: 默认值合理 (3次, 1s起步, 30s封顶)
  max_attempts=3
  initial_delay=1.0
  max_delay=30.0
  jitter=True

with_retry(fn, config)            ──→  C7: 第1次就成功 → 只调1次 (不浪费)
  │                                ──→  C8: 前2次失败, 第3次成功 → 返回结果
  │                                ──→  C9: 3次都失败 → 抛出原始错误
  │                                ──→  C10: 429状态码 → 自动重试, 200时返回
  │
指数退避算法                       ──→  C4: delay = 1s → 2s → 4s (翻倍)
                                   ──→  C5: 永远不超过 max_delay
                                   ──→  C6: 加随机抖动, 防止雷群效应

retry_api_call(fn, tool_name)     ──→  C11-C12: 函数式接口 + 失败报告尝试次数
```

**关键验证点：**
- ✅ 429/502/503/504 自动重试，不打扰用户
- ✅ 指数退避避免打爆 API
- ✅ 3 次失败后把原始错误给小模型（而不是吞掉）

---

### 📦 模块 D: crypto_safety.py — "区块链交易的安全护栏"

**解决什么问题？**
> 1inch swap 不检查余额就发交易，Aave 存款不看健康因子，
> 交易成功后不等确认就告诉用户"完成了"。现在加 pre/post 检查。

```
crypto_safety.py                       test_patches_crypto_safety.py (16 tests)
────────────────                       ────────────────────────────
get_finality_info(chain)          ──→  D1: ETH = 12区块 × 12秒 ≈ ~3分钟
  │ "交易发出后要等多久才算真的成功"  ──→  D2: 未知链返回安全默认值 (非崩溃)
  │                                ──→  D3: 覆盖 8 条主流链 (ETH/BSC/ARB/...)
  │                                ──→  D4: L2 提示 7 天挑战期

format_finality_message(chain,tx) ──→  D5: 包含 ⏳ emoji + 截短hash + 区块浏览器链接
                                   ──→  D6: L2 额外警告跨链提现延迟

estimate_gas_needed(operation)    ──→  D7: ETH转账=21000 + 20%缓冲
  │ "这笔操作大概要多少Gas"         ──→  D8: 未知操作用 200K 安全值
  │                                ──→  D9: 覆盖 7 种常见操作 (swap/approve/...)

suggest_slippage(pair, volume)    ──→  D10: 稳定币对 → 0.1% (USDC↔USDT)
  │ "滑点该设多少"                  ──→  D11: 主流对 → 0.5% (ETH/USDC)
  │                                ──→  D12: 看24h成交量判断流动性
  │                                ──→  D13: 未知代币 → 1% 保守默认
  │                                ──→  D14: 建议附带人话解释

generate_verification_checklist() ──→  D15-D16: 交易后生成核验清单
  │ "交易发出后该检查什么"                (调哪个余额接口、预期变化多少)
```

**关键验证点：**
- ✅ 不知道的链不会崩溃（安全默认值）
- ✅ 滑点建议基于交易对类型 + 流动性，不是一刀切
- ✅ 每笔交易后生成验证清单，小模型知道该调什么工具确认

---

### 📦 模块 E: 端到端流程 — "所有模块串起来能跑通吗"

```
test_patches_e2e.py (7 tests)
─────────────────────────────

E1: 查价格流程
   API 502 → retry模块自动重试 → 成功 → response.ok()格式化输出
   验证: retry + response 配合

E2: Swap 完整流程 (最重要的测试)
   suggest_slippage → estimate_gas → 执行swap → 
   generate_verification_checklist → format_finality_message
   验证: crypto_safety 4个函数串联

E3: Swap 被拒
   余额不足 → InsufficientBalanceError → 自动算差额 → 建议"先充值"
   验证: errors + crypto_safety 配合

E4: 多链余额查询
   3条链成功 + 1条链超时 → 成功的格式化 + 失败的报错
   验证: response + errors 混合场景

E5: 重试耗尽
   3次全失败 → 结构化错误 (不是空值/崩溃)
   验证: retry + errors 配合

E6: 模块无冲突
   4个模块同时 import, 无命名冲突
   验证: 工程纪律

E7: 输出一致性
   错误和失败响应都以 ❌ 开头, 小模型一眼识别
   验证: errors + response 格式统一
```

---

## 🎯 "这些测试够不够" 的判断标准

### ✅ 覆盖了的

| 场景 | 测试数 | 覆盖率 |
|------|--------|--------|
| 错误分类 — 小模型能理解出了什么错 | 14 | 所有 13 种异常类型 |
| 返回格式 — 小模型能解析成功结果 | 14 | dict/list/scalar + 格式化器 |
| 网络重试 — 瞬态失败自动恢复 | 12 | 成功/部分失败/全失败 |
| 链上安全 — 交易前后的护栏 | 16 | 8条链 × 7种操作 × 滑点 |
| 端到端 — 模块组合工作 | 7 | 5种真实 crypto 流程 |

### ⚠️ 还没覆盖的（诚实说明）

| 缺口 | 原因 | 风险等级 |
|------|------|---------|
| 真实 RPC 调用测试 | 需要测试网节点，不是纯逻辑 | 中 — Phase 2 做 |
| 对原仓库代码的直接 patch 测试 | 补丁是示例代码，还没 merge 进去 | 高 — 需要 PR |
| 性能/延迟测试 | 需要 benchmark 框架 | 低 — 逻辑正确优先 |
| prompt injection 防御 | 需要 LLM-in-the-loop 测试 | 中 — 需要专项方案 |

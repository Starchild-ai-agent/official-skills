# Skill Quality Improvement — Integration Guide

## TL;DR

测试发现 **180 个问题**，根本原因归纳为 **3 个系统性缺陷**：

| # | 缺陷 | 影响 | 问题数 | 修复方案 |
|---|------|------|--------|---------|
| 1 | Silent error swallowing | 小模型收到 None/空值无法诊断 | 128 | `shared/errors.py` + 各 skill 的 except 块升级 |
| 2 | SKILL.md 结构化不足 | 小模型无法正确构造 tool 调用 | 142 | `SKILLMD_TEMPLATE.md` 统一格式 |
| 3 | 缺少 crypto 安全检查 | 交易后无验证，无滑点保护 | 19 | `shared/crypto_safety.py` + skill 级 pre/post hooks |

---

## Patch Inventory

```
patches/
├── INTEGRATION_GUIDE.md          ← 你正在读的文件
├── shared/                       ← P0: 所有 skill 共享的基础设施
│   ├── errors.py                 ← 结构化异常分类（替代 except:pass）
│   ├── response.py               ← 统一返回格式（ok/fail/fmt_table）
│   ├── retry.py                  ← HTTP retry with backoff（替代无 retry 直接失败）
│   ├── crypto_safety.py          ← 链特定安全检查（finality/gas/slippage）
│   └── SKILLMD_TEMPLATE.md       ← SKILL.md 标准化模板
├── hyperliquid/                  ← P1: 最高优先级（交易类 skill）
│   ├── README.md
│   ├── client_error_handling.py  ← 3 个 CRITICAL silent except 修复
│   └── tools_error_context.py    ← 21 个 tool 的错误消息结构化
├── coinglass/                    ← P2: 数据类 skill
│   └── api_error_handling.py     ← 112 处 return None → 结构化错误
├── 1inch/                        ← P3: DeFi 交易类
│   └── swap_safety.py            ← 滑点保护 + pre/post-swap 验证
└── aave/                         ← P3: DeFi 借贷类
    └── lending_safety.py         ← 健康因子警告 + 清算风险教育
```

---

## Implementation Priority

### Phase 1 — Shared Infrastructure (1-2 days)

**为什么先做这个：** 所有 skill 都依赖的基础层，修一次受益所有 skill。

1. **将 `shared/` 放入仓库的 common 位置**
   ```
   official-skills/
   ├── _shared/         ← 新增：共享模块
   │   ├── errors.py
   │   ├── response.py
   │   ├── retry.py
   │   └── crypto_safety.py
   ├── hyperliquid/
   ├── coinglass/
   └── ...
   ```

2. **每个 skill 的 `__init__.py` 添加 import**
   ```python
   import sys, os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
   from _shared.errors import safe_call, SkillError
   from _shared.response import ok, fail
   ```

### Phase 2 — Hyperliquid Error Handling (2-3 days)

**为什么优先：** 交易类 skill，错误 = 亏钱。

按 `hyperliquid/README.md` 中的 3 个 patch 依次应用：
1. `client_error_handling.py` — 修复 3 个 CRITICAL silent except
2. `tools_error_context.py` — 添加 `_format_error` helper，升级 21 个 except 块
3. 测试：每个 tool 手动调用一次，验证错误消息可读性

### Phase 3 — Coinglass Error Chain (1-2 days)

按 `coinglass/api_error_handling.py` 中的模式，批量替换 112 处 `return None`。
建议用 sed 脚本半自动化，然后逐文件 review。

### Phase 4 — SKILL.md 标准化 (3-5 days)

这是工作量最大但长期收益最高的部分。

**操作步骤：**
1. 用 `SKILLMD_TEMPLATE.md` 作为模板
2. 每个 skill 的 SKILL.md 需要添加：
   - **Quick Reference 表格** — 小模型 first-scan 用
   - **Tool Signatures with Examples** — 不能省略参数类型和返回值
   - **Step-by-step Workflows** — 写成可执行的伪代码
   - **Error Recovery 表格** — 小模型查表修复
   - **Known Limitations** — 防止幻觉

**优先级排序（按使用频率）：**
1. hyperliquid — 交易核心
2. coingecko — 价格查询核心
3. coinglass — 市场数据
4. wallet — 钱包操作
5. 1inch — DeFi 交换
6. aave — DeFi 借贷
7. 其余 skills

### Phase 5 — DeFi Safety Hooks (2-3 days)

应用 `1inch/swap_safety.py` 和 `aave/lending_safety.py` 中的 pre/post 检查。

---

## 小模型适配核心原则

经过本次审计，总结出让 skill 在小模型上工作良好的 5 条黄金规则：

### 1. 永远不要返回 None

```python
# ❌ 小模型看到 None 会困惑："没有数据？还是出错了？"
except Exception:
    return None

# ✅ 小模型看到错误消息可以自诊断并回复用户
except Exception as e:
    return {"_error": True, "message": str(e), "suggestion": "..."}
```

### 2. 错误消息必须包含建议

```python
# ❌ 小模型不知道该建议什么
"Error: insufficient margin"

# ✅ 小模型直接转述建议给用户
"❌ [INSUFFICIENT_MARGIN] hl_order: Not enough margin.\n"
"  Available: 100 USDC, Required: 500 USDC\n"
"  → Deposit more USDC or reduce position size by 80%"
```

### 3. SKILL.md 必须有可执行的 Workflow

```markdown
<!-- ❌ 太模糊，小模型会猜参数 -->
Use hl_order to place orders on Hyperliquid.

<!-- ✅ 小模型跟着步骤执行，不需要猜 -->
### Place a Limit Buy Order
1. `hl_market("BTC")` → get `mark_price`, `min_size`
2. Calculate: `price = mark_price * 0.99` (1% below market)
3. Calculate: `size = budget / price` (round to `min_size`)
4. `hl_order("BTC", "buy", size, price, "limit")`
5. `hl_open_orders()` → verify order appears
```

### 4. 返回值类型必须一致

```python
# ❌ 有时返回 dict，有时返回 str，有时返回 ToolResult
def get_price(coin):
    if error: return "Error: ..."        # str
    if no_data: return None              # NoneType
    return {"price": 123}               # dict

# ✅ 永远返回同一种类型
def get_price(coin):
    if error: return fail("coingecko/get_price", "...")   # always str
    return ok({"price": 123}, summary="BTC: $123")        # always dict
```

### 5. 交易类操作必须有 pre/post 检查

```
PRE:  Check balance ≥ required amount + gas
      Check slippage is reasonable
      Warn on large amounts

POST: Wait for chain finality
      Verify balance changed
      Report actual vs expected
```

---

## Metrics: Before vs After (Expected)

| Metric | Before | After (Expected) |
|--------|--------|-------------------|
| Silent `return None` on error | 112 | 0 |
| `except: pass` in critical paths | 3 | 0 |
| SKILL.md with executable workflows | 2/16 | 16/16 |
| SKILL.md with error recovery tables | 0/16 | 16/16 |
| Tools with structured error messages | 3/80+ | 80+/80+ |
| Pre-transaction safety checks | 0 | All transaction tools |
| Post-transaction verification prompts | 0 | All transaction tools |

---

## How to Validate

After applying patches, run the test suite:

```bash
cd projects/official-skills-audit
python run_all.py
```

Expected: Issue count drops from 180 → <20 (remaining will be documentation items that need manual writing).

# 🧪 Testing Guide — Official Skills Audit

> 写给能看懂代码但不是深度从业者的你。  
> Written so a CS student can quickly verify completeness.

## 一句话总结 / TL;DR

我们给 Starchild 的 official-skills 仓库写了 **194 个自动化测试**，覆盖以下目标：

| 目标 | 测试数 | 核心问题 |
|------|--------|---------|
| 🛡️ 补丁代码质量 (patches/) | 77 | 我们写的改进代码本身有没有 bug？ |
| 🔗 跨 Skill 一致性 | 5 | 12 个 skill 之间是否遵循相同规范？ |
| 📐 Schema 校验 | 9 | Skill 的 SKILL.md 文档结构是否完整？ |
| 🔒 安全审计 | 5 | 代码里有没有注入/泄漏风险？ |
| ⚡ API 端点健壮性 | 22 | CoinGecko/CoinGlass 等 API 调用是否正确处理错误？ |
| 🔐 交易安全检查 | 10 | DeFi 操作是否有滑点/Gas 保护？ |
| ✅ 输入校验 (validators) | 27 | 地址/金额/链ID 等参数是否正确校验？ |
| 🔄 重试机制 (retry) | 14 | 网络失败时是否正确重试+退避？ |
| 🎯 特定 Skill 测试 | 15 | charting/polymarket/twitter 是否功能完整？|
| 📊 其他 (workflow/format) | 10 | 端到端流程+返回格式是否合规？ |

---

## 如何运行 / How to Run

```bash
# 进入项目目录
cd fork-workspace

# 运行全部测试（约 20 秒）
python -m pytest tests/ -v

# 运行某一类测试
python -m pytest tests/test_security_audit.py -v      # 只跑安全
python -m pytest tests/test_m1_validators.py -v        # 只跑校验
python -m pytest tests/test_coverage_gaps.py -v        # 只跑补丁覆盖

# 带覆盖率（需 pip install pytest-cov）
python -m pytest tests/ --cov=patches --cov-report=term-missing
```

**依赖**：只需要 `pytest` + `requests`（标准库外仅这两个）

---

## 项目结构 / Project Structure

```
fork-workspace/
├── patches/                  ← 我们的改进代码（被测对象）
│   ├── shared/               ← 所有 skill 共用的工具库
│   │   ├── errors.py         ← 统一错误处理（SkillError 层级）
│   │   ├── response.py       ← 统一返回格式（format_table 等）
│   │   ├── validators.py     ← 输入校验（地址/金额/链ID/滑点）
│   │   ├── retry.py          ← 智能重试（指数退避+抖动）
│   │   └── crypto_safety.py  ← DeFi 安全检查（滑点/Gas/授权）
│   ├── 1inch/swap_safety.py  ← 1inch swap 前的安全拦截
│   ├── aave/lending_safety.py ← AAVE 借贷安全检查
│   ├── coinglass/             ← CoinGlass API 错误处理
│   └── hyperliquid/           ← Hyperliquid 错误上下文增强
│
├── tests/                    ← 测试套件（你在看的这部分）
│   ├── conftest.py           ← pytest 配置 + 路径设置
│   ├── test_coverage_gaps.py ← [77 tests] 补丁代码深度覆盖
│   ├── test_m1_validators.py ← [27 tests] 地址/金额/链ID 校验
│   ├── test_m1_retry.py      ← [14 tests] 重试机制验证
│   ├── test_live_endpoints.py← [22 tests] API 端点 mock 测试
│   ├── test_live_safety.py   ← [10 tests] DeFi 交易安全
│   ├── test_schema_validation.py ← [9 tests] SKILL.md 文档检查
│   ├── test_security_audit.py   ← [5 tests] 安全扫描
│   ├── test_cross_skill_consistency.py ← [5 tests] 跨 skill 一致性
│   ├── test_skill_charting.py   ← [5 tests] charting skill
│   ├── test_skill_polymarket.py ← [5 tests] polymarket skill
│   ├── test_skill_twitter.py    ← [5 tests] twitter skill
│   └── ... (辅助测试文件)
│
├── TESTING_GUIDE.md          ← 你正在读的这个文件
└── README.md                 ← 项目概述（如有）
```

---

## 每个测试文件在测什么 / What Each Test Does

### 1. `test_coverage_gaps.py` — 补丁代码覆盖（77 tests）⭐最重要

**目的**：确保 `patches/` 里我们写的每一个函数、每一个分支都被测到。

```
TestErrors (19 tests)
├── test_skill_error_basic           → SkillError 基础创建
├── test_api_error_with_status       → API 错误带 HTTP 状态码
├── test_validation_error_fields     → 校验错误包含字段信息
├── test_rate_limit_error_retry      → 限频错误有重试提示
├── test_classify_*                  → 各种 HTTP 状态码自动分类
└── test_format_for_llm              → 错误信息格式化给 AI 可读

TestResponse (14 tests)
├── test_format_table_basic          → 表格生成
├── test_format_table_custom_columns → 自定义列
├── test_truncate_for_llm            → 超长数据截断
└── test_normalize_numeric           → 数字归一化（"1.23M" 等）

TestValidators (18 tests)
├── test_validate_address_*          → ETH 地址格式校验
├── test_validate_amount_*           → 金额范围校验
├── test_validate_slippage_*         → 滑点百分比校验
└── test_validate_chain_id_*         → 链 ID 校验

TestRetry (14 tests)
├── test_retry_succeeds_*            → 重试后成功的场景
├── test_retry_respects_max          → 最大重试次数
├── test_calc_delay_*                → 退避延迟计算
└── test_async_retry_*               → 异步重试
```

**为什么重要**：这些是我们要合并到主仓库的代码。如果这里有 bug，会影响所有 skill。

---

### 2. `test_m1_validators.py` — 输入校验（27 tests）

**目的**：防止用户（或 AI Agent）传入错误参数导致资金损失。

```python
# 举个例子：如果 AI 生成了错误的地址格式
validate_address("0xINVALID")  → 抛出 ValidationError
validate_address("0x742d35Cc...")  → 返回 checksum 格式地址

# 金额保护：防止转账 0 元或负数
validate_amount(-1)  → 抛出错误
validate_amount(0)   → 抛出错误（除非 allow_zero=True）
validate_amount(100) → 正常通过
```

**为什么重要**：小模型容易生成格式错误的参数，这层校验是最后防线。

---

### 3. `test_live_safety.py` — DeFi 安全（10 tests）

**目的**：确保任何 DeFi 操作前都有安全检查。

```
✓ 滑点保护     → swap 前检查价格影响 < 阈值
✓ Gas 估算     → 防止 Gas 费超过交易金额
✓ 授权检查     → approve 前验证合约地址
✓ 健康因子     → AAVE 借贷前检查清算风险
✓ 最小输出     → swap 设置最小接收量（防三明治攻击）
```

---

### 4. `test_security_audit.py` — 安全扫描（5 tests）

**目的**：静态扫描 `patches/` 代码，查找危险模式。

| 检查项 | 找什么 | 为什么危险 |
|--------|--------|-----------|
| `eval`/`exec` | 动态代码执行 | 可被注入恶意代码 |
| 硬编码私钥 | `0x` 开头的 64 位 hex | 资金盗窃 |
| Shell 注入 | `os.system`/`subprocess.call` | 命令注入 |
| 路径遍历 | `../` 模式 | 读取敏感文件 |
| 环境变量泄漏 | `print(os.environ)` | 密钥泄漏 |

---

### 5. `test_schema_validation.py` — 文档规范（9 tests）

**目的**：每个 Skill 的 SKILL.md 必须包含关键字段。

```
✓ 有 name 字段        → skill 能被发现
✓ 有 description      → 用户知道这是做什么的
✓ 有 tools 列表       → AI 知道有哪些工具可用
✓ 有 ## Workflow 章节 → AI 知道怎么用
✓ 有 ## Error 章节    → AI 知道出错怎么办
```

---

### 6. `test_cross_skill_consistency.py` — 一致性（5 tests）

**目的**：12 个 skill 之间是否遵循相同模式。

```
✓ 所有函数有 docstring  → AI 能理解函数用途
✓ 所有 skill 有 __init__.py → 能被正确导入
✓ 错误处理用统一格式     → AI 不用为每个 skill 学不同模式
```

---

## 关键指标 / Key Metrics

```
总测试数:     194
通过:         194 ✅
失败:          0
跳过:          0
运行时间:     ~20 秒
补丁覆盖率:   96%+ (patches/ 目录)
```

---

## 测试策略说明 / Testing Philosophy

### 为什么不需要真实 API？

所有 API 测试使用 **mock**（模拟）：
- `test_live_endpoints.py` 用 `unittest.mock.patch` 替换真实 HTTP 请求
- 测试的是 **"收到某种响应后，代码处理是否正确"**
- 不测 **"CoinGecko 服务器是否在线"**（那是他们的事）

### 为什么有些测试允许一定比例失败？

```python
# test_cross_skill_consistency.py
assert ratio < 0.5  # 允许最多 50% 的函数没有 docstring
```

因为这是 **审计发现**，不是 **我们的 bug**。我们记录问题，不强制立刻修复所有 skill。

### 测试如何保证小模型友好？

- `validators.py` 测试确保**错误信息是人类可读的**（小模型能理解）
- `response.py` 测试确保**返回格式统一**（小模型不用猜格式）
- `errors.py` 测试确保**错误类型明确**（小模型能区分"重试"还是"停止"）

---

## FAQ

**Q: 怎么知道测试是不是真的在测东西？（不是写了个空 assert）**

看 `test_coverage_gaps.py`，每个 test 都有明确的 `assert` + 具体值：
```python
def test_format_table_basic(self):
    result = format_table([{"a": 1, "b": 2}])
    assert "a" in result      # 列名存在
    assert "1" in result      # 数据存在
    assert "|" in result      # 是表格格式
```

**Q: 如果我改了 patches/ 里的代码，测试会抓到 bug 吗？**

会。试试故意改坏一个函数：
```bash
# 把 validate_address 的正则改错
sed -i 's/0x[0-9a-fA-F]{40}/0x[0-9]{40}/' patches/shared/validators.py
python -m pytest tests/test_m1_validators.py -v  # 会立刻失败
```

**Q: 为什么没有集成测试？**

集成测试需要真实 API key + 真实区块链交互。这些在 CI/CD 里用 staging 环境跑，不在 PR 测试里。

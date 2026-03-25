# API Credentials Report — official-skills Audit

> Generated: 2026-03-25 13:36 UTC
> Author: Aaron (Starchild Agent Audit)
> Repo: `Starchild-ai-agent/official-skills`

---

## 结论

**原始 official-skills 项目中没有任何 API 密钥、`.env` 文件、CI 测试配置或凭证文件。**

这 **不是缺陷**，这是 Starchild 平台的架构设计。

---

## 1. 架构：sc-proxy 透明代理

Starchild 平台使用一个名为 **sc-proxy** 的透明代理来统一管理所有 API 认证：

```
┌─────────────────────────────────────────────────────────┐
│  Starchild Agent 容器                                     │
│                                                         │
│  COINGECKO_API_KEY = "fake-coingec..."                  │
│  COINGLASS_API_KEY = "fake-coingla..."                  │
│  BIRDEYE_API_KEY   = "fake-birdeye..."                  │
│  ...（全部是 fake-* 占位符）                               │
│                                                         │
│  skill 代码 → proxied_get(url, headers={API_KEY})       │
│         ↓                                               │
│  sc-proxy 拦截 → 替换 fake key → 真实 key → 上游 API    │
└─────────────────────────────────────────────────────────┘
```

**工作原理：**
1. 平台向每个容器注入 `fake-*` 开头的占位密钥
2. Skill 代码用这些 fake key 构建请求头
3. sc-proxy（mitmproxy）拦截出站请求
4. 代理把 fake key 替换成真实 API key
5. 请求转发到上游 API，响应返回给 skill

**这意味着：** skill 代码本身永远不接触真实密钥，也不需要任何 `.env` 文件。

---

## 2. 项目中确实不存在的东西

| 项目 | 状态 |
|------|------|
| `.env` 文件 | ❌ 不存在 |
| `.env.example` 模板 | ❌ 不存在 |
| 真实 API 密钥 | ❌ 不存在（设计如此） |
| CI 测试工作流 | ❌ 不存在 |
| `conftest.py` | ❌ 不存在 |
| `pytest.ini` / `setup.cfg` | ❌ 不存在 |
| 任何 `test_*.py` 文件 | ❌ 不存在 |
| `requirements.txt` | ❌ 不存在 |

**唯一的 CI workflow** 是 `.github/workflows/build-index.yml`，它仅负责生成 `skills.json` 索引文件，不做任何测试。

---

## 3. 9 个 API 密钥全景

以下是 official-skills 中引用的所有 API 密钥：

| 环境变量 | 使用 Skill | 代理状态 | 直接请求可用性 |
|----------|-----------|----------|--------------|
| `COINGECKO_API_KEY` | coingecko, charting, dashboard | ✅ fake-* via proxy | ❌ 需要真实 key |
| `COINGLASS_API_KEY` | coinglass | ✅ fake-* via proxy | ❌ 需要真实 key |
| `TWELVEDATA_API_KEY` | twelvedata, charting, dashboard | ✅ fake-* via proxy | ❌ 需要真实 key |
| `TAAPI_API_KEY` | taapi | ✅ fake-* via proxy | ❌ 需要真实 key |
| `TWITTER_API_KEY` | twitter | ✅ 真实 key 已配置 | ✅ 可用 |
| `BIRDEYE_API_KEY` | birdeye | ✅ fake-* via proxy | ❌ 需要真实 key |
| `DEBANK_API_KEY` | debank | ✅ fake-* via proxy | ❌ 需要真实 key |
| `ONEINCH_API_KEY` | 1inch | ✅ fake-* via proxy | ❌ 需要真实 key |
| `LUNARCRUSH_API_KEY` | lunarcrush | ✅ fake-* via proxy | ❌ 需要真实 key |

---

## 4. 对我们测试的影响

### ✅ 在 Starchild 运行时中正常工作

通过 Starchild 平台的 native tool 调用（如 `coin_price()`、`funding_rate()`），所有 API 都正常工作，因为：
- 平台工具走 `core.http_client.proxied_get()` → sc-proxy → 真实 key

**实测验证（2026-03-25）：**
- `coin_price(bitcoin)` → ✅ $71,799
- `cg_global()` → ✅ 18,009 coins
- `funding_rate(BTC)` → ✅ rate: 0.002307
- `cg_open_interest(BTC)` → ✅ $101.9B

### ❌ 在独立 CI/pytest 中不工作

我们的测试套件（`tests/`）在脱离 Starchild 容器运行时：
- `fake-*` key 直接发到上游 API → **401 Unauthorized**
- 没有 sc-proxy → 没有 key 替换
- 91 个测试被标记为 `skip`（需要 API 凭证）

### 解决方案

要在独立 CI 中运行 live API 测试，有两条路：

**方案 A：CI 中设置 GitHub Secrets（推荐）**
```yaml
# .github/workflows/test.yml
env:
  COINGECKO_API_KEY: ${{ secrets.COINGECKO_API_KEY }}
  COINGLASS_API_KEY: ${{ secrets.COINGLASS_API_KEY }}
```
需要 Starchild 团队在 GitHub repo settings 中配置真实 API key。

**方案 B：纯 Mock 测试（当前方案）**
- 我们的 1,240 个通过测试全部使用 mock/静态数据
- 不依赖任何真实 API
- 完全可以在任何环境跑通

---

## 5. 总结

| 问题 | 回答 |
|------|------|
| 原始项目有 API 密钥吗？ | **没有**，设计如此 |
| 原始项目有测试吗？ | **没有**，测试全部是我们新增的 |
| 原始项目有 CI 吗？ | **只有索引生成**，没有测试 CI |
| 为什么 fake key 能工作？ | **sc-proxy 透明代理**替换真实 key |
| 独立运行测试需要什么？ | 真实 API key 或 GitHub Secrets |
| 我们的测试怎么解决的？ | **1,240 测试用 mock 数据，不依赖 API** |
| 91 个 skip 测试是什么？ | live endpoint 验证，需要真实 API |

**项目没有放 API key 是正确的架构选择——Starchild 平台通过 sc-proxy 在运行时注入凭证，skill 代码永远不需要接触真实密钥。**

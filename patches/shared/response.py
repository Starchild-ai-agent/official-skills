"""
Standardized Response Wrapper for All Skills
=============================================
解决问题: 12 个 skill 有 6 种不同返回格式，小模型无法预测解析策略。
方案: 统一返回 ToolResult，自动格式化为小模型友好的结构。

用法:
    from shared.response import ok, fail, fmt_table, fmt_price, fmt_balance

    # 成功返回 — 自动构建 markdown
    return ok(data={"price": 1234.56, "change_24h": "+5.2%"}, summary="BTC at $1,234.56")

    # 失败返回 — 给小模型明确的错误上下文
    return fail("hyperliquid/hl_order", "Insufficient margin", got={"available": 100}, need={"required": 500})
"""

from typing import Any
# NOTE: ToolResult is the platform-provided response object
# This module provides factory functions that WRAP it consistently


def ok(data: Any, summary: str = "", tool_name: str = "") -> dict:
    """
    Standard success response.
    - data: structured result (dict/list)
    - summary: one-line human-readable summary (小模型直接用这行回复用户)
    """
    result = {"status": "ok"}
    if summary:
        result["summary"] = summary
    if isinstance(data, dict):
        result.update(data)
    elif isinstance(data, list):
        result["items"] = data
        result["count"] = len(data)
    else:
        result["value"] = data
    return result


def fail(tool_name: str, reason: str,
         got: Any = None, need: Any = None,
         suggestion: str = "", code: str = "") -> str:
    """
    Standard error response — optimized for small model diagnosis.
    返回结构化错误字符串，小模型可以直接理解并给用户解释。

    Args:
        tool_name: "skill/tool" 格式，如 "hyperliquid/hl_order"
        reason: 人类可读的错误原因
        got: 实际收到的值 (optional)
        need: 期望的值 (optional)
        suggestion: 建议的修复步骤 (optional)
        code: 错误代码 (optional, 如 "INSUFFICIENT_MARGIN")
    """
    parts = [f"❌ {tool_name} failed: {reason}"]
    if code:
        parts[0] = f"❌ [{code}] {tool_name} failed: {reason}"
    if got is not None:
        parts.append(f"  Got: {got}")
    if need is not None:
        parts.append(f"  Expected: {need}")
    if suggestion:
        parts.append(f"  → {suggestion}")
    return '\n'.join(parts)


def fmt_price(symbol: str, price: float, change_24h: float = None,
              volume_24h: float = None, source: str = "") -> str:
    """Format price data for consistent display across skills"""
    sign = "+" if change_24h and change_24h > 0 else ""
    parts = [f"{symbol}: ${price:,.2f}" if price >= 1 else f"{symbol}: ${price:.6f}"]
    if change_24h is not None:
        parts.append(f"({sign}{change_24h:.1f}%)")
    if volume_24h:
        parts.append(f"Vol: ${_fmt_large(volume_24h)}")
    if source:
        parts.append(f"[{source}]")
    return ' '.join(parts)


def fmt_balance(balances: list[dict], title: str = "Balances") -> str:
    """
    Format balance list into markdown table.
    Each item: {symbol, amount, usd_value, chain?}
    """
    if not balances:
        return f"{title}: No assets found"

    lines = [f"**{title}**", "| Asset | Amount | USD Value |", "|-------|--------|-----------|"]
    total_usd = 0
    for b in balances:
        usd = b.get('usd_value', 0) or 0
        total_usd += usd
        chain_tag = f" ({b['chain']})" if b.get('chain') else ""
        lines.append(f"| {b['symbol']}{chain_tag} | {_fmt_amount(b['amount'])} | ${usd:,.2f} |")
    lines.append(f"| **Total** | | **${total_usd:,.2f}** |")
    return '\n'.join(lines)


def fmt_table(rows: list[dict], columns: list[str] = None, title: str = "") -> str:
    """Generic dict-list → markdown table"""
    if not rows:
        return f"{title}: No data" if title else "No data"

    cols = columns or list(rows[0].keys())
    lines = []
    if title:
        lines.append(f"**{title}**")
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for row in rows[:50]:  # Cap at 50 rows to avoid flooding context
        vals = [str(row.get(c, "")) for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    if len(rows) > 50:
        lines.append(f"*...and {len(rows)-50} more rows*")
    return '\n'.join(lines)


def _fmt_large(n: float) -> str:
    if n >= 1e9:
        return f"{n/1e9:.1f}B"
    if n >= 1e6:
        return f"{n/1e6:.1f}M"
    if n >= 1e3:
        return f"{n/1e3:.1f}K"
    return f"{n:.0f}"


def _fmt_amount(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1000:
        return f"{n:,.2f}"
    if n >= 1:
        return f"{n:.4f}"
    if n >= 0.0001:
        return f"{n:.6f}"
    return f"{n:.8f}"

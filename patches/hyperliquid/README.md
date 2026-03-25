# Hyperliquid Patches

## Problem Summary

Hyperliquid skill 有 21 个 `except Exception` 分布在 `client.py` 和 `tools.py` 中，其中：
- **3 个 CRITICAL**: `except: pass` / `except: return default` 在关键路径（余额查询、订单验证）上吞掉错误
- **18 个 HIGH**: 所有 tool 函数用 `except Exception as e: return ToolResult(success=False, error=str(e))` 但 `str(e)` 对小模型不够友好

## Patches

### 1. client_error_handling.py
修复 `client.py` 中的 3 个 CRITICAL silent exception:
- Line 164: spot_meta 加载失败 → 不应静默回退空 dict，应该 log + 标记降级
- Line 247: _resolve_any_asset → 正常的 fallthrough 逻辑，实际上OK（只是 ValueError 作为控制流）
- Line 331/596: abstraction_state 查询失败 → 不应静默假设 "default"

### 2. tools_error_context.py 
升级 `tools.py` 中 21 个 tool 的 except 块，添加结构化错误上下文。

### 3. order_validation.py
修复 Line 666 的 non-blocking validation warning，这应该对小模型可见。

# CoinGecko F→C 优化方案

**当前:** Loss=12.200 (F) → **目标:** Loss<3.0 (C)，需ΔL=-9.2

## 损失分解

| 维度 | 原始值 | 权重 | 加权值 | 占比 |
|------|--------|------|--------|------|
| L_task | 0.783 | ×10 | **7.83** | **64%** |
| L_density | 0.447 | ×5 | **2.24** | **18%** |
| L_efficiency | 0.529 | ×3 | **1.59** | **13%** |
| L_cost | 0.549 | ×1 | **0.55** | **5%** |

## 根因分析

### 问题1: L_task=7.83 — 18个函数缺少 try/except (64%的Loss)

L_task 用 `n/(n+k)` 公式计算(k=5)，18个 missing_error_guard 直接导致 0.783。
**这是最高杠杆点**：修完全部18个 → L_task=0，直接砍掉7.83。

**受影响文件:**
| 文件 | 缺失数 |
|------|--------|
| exchanges.py | 4 |
| infrastructure.py | 4 |
| coins.py | 4 |
| nfts.py | 3 |
| global_data.py | 2 |
| search.py | 1 |

### 问题2: L_density=2.24 — 38个函数无limit参数 + 3个返回raw JSON (18%)

密度问题分两块：
- **no_limit_param ×38**: API调用不限制返回数据量，小模型context爆炸
- **raw_json_return ×3**: contracts.py/exchanges.py/coins.py 直接返回未过滤的API响应

### 问题3: L_efficiency=1.59 — 与L_task同源

效率损失同样来自 missing_error_guard，修复L_task会同时降低L_efficiency。

## 修复优先级（按ΔL/effort排序）

### Phase 1: 修error guards → 预计ΔL≈-9.4
**ROI最高，一次性解决64%+13%的Loss**

每个文件加 try/except 包裹API调用：
```python
# Before
def get_exchanges(per_page=100, page=1):
    response = proxied_get(url, params=params)
    return response.json()

# After  
def get_exchanges(per_page=100, page=1):
    try:
        response = proxied_get(url, params=params)
        return response.json()
    except Exception as e:
        return {"error": str(e)}
```

修复顺序(共6个文件18个函数):
1. `exchanges.py` — 4个函数
2. `infrastructure.py` — 4个函数
3. `coins.py` — 4个函数
4. `nfts.py` — 3个函数
5. `global_data.py` — 2个函数
6. `search.py` — 1个函数

### Phase 2: 加limit参数 → 预计ΔL≈-1.0
给高流量endpoint加 `limit` / `max_results` 参数：
- coin_prices.py (3)
- market_discovery.py (3)
- derivatives.py (3)
- 其余文件按优先级

### Phase 3: 过滤raw JSON → 预计ΔL≈-0.3
3个文件添加field filter，只返回Agent需要的字段。

## 预测

| 阶段 | 完成后Loss | 预计等级 |
|------|-----------|---------|
| 当前 | 12.200 | F |
| Phase 1完成 | ~2.8 | **C** ✅ |
| Phase 2完成 | ~1.8 | C (接近B) |
| Phase 3完成 | ~1.5 | B |

**结论: Phase 1 alone 就足以达到C级。这是唯一的关键路径。**

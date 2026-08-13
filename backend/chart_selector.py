"""
图表类型自动选择 —— 纯启发式规则。
不调 LLM：选图表是确定性问题，规则匹配就够了。
"""

import re

from backend.schemas import ColumnMeta, ColumnType


def select(question: str, columns: list[ColumnMeta],sql: str = "") -> str:
    """根据用户问题和列类型，返回推荐的图表类型。

    Returns:
        "pie" | "line" | "bar" | "scatter" | "table"
    """
    col_names = [c.name for c in columns]
    col_types = {c.name: c.dtype for c in columns}

    text_cols = [n for n in col_names if col_types[n] == ColumnType.STRING]
    num_cols = [n for n in col_names if col_types[n] in (ColumnType.INTEGER, ColumnType.FLOAT)]
    date_cols = [n for n in col_names if col_types[n] == ColumnType.DATETIME]
    # 0. 明细筛选（无 GROUP BY / 无聚合函数）→ table，最高优先级
    #    "退款情况怎么样" → SELECT * WHERE 是否退款=1，是列明细，不是统计
    upper = sql.upper()
    has_group_by = "GROUP BY" in upper
    has_agg_func = re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", upper) is not None
    has_aggregation = has_group_by or has_agg_func
    if not has_aggregation:
        # 明细查询默认 table；例外：纯数值多列（相关性）→ scatter
        if len(num_cols) >= 2 and not text_cols and not date_cols:
            return "scatter"
        return "table"
    # 1. 问占比 + ≥1 文本列 + ≥1 数值列 → 饼图
    pie_kw = {"占比", "比例", "百分比", "分布", "份额", "比重", "构成"}
    if any(kw in question for kw in pie_kw) and text_cols and num_cols:
        return "pie"

    # 2. 问趋势 + 有日期列 → 折线图（看变化方向）
    trend_kw = {"趋势", "变化", "走势", "增长", "下降", "随时间"}
    if any(kw in question for kw in trend_kw) and date_cols:
        return "line"

    # 3. 时间分组对比 + 有数值列 → 柱状图（各月/每月…，逐个时间点对比大小）
    group_time_kw = {"各月", "每月", "逐月", "各年", "每年", "逐年", "各季度", "每季度", "每日", "每天", "每周", "逐日", "按季度", "按月", "按年", "按日", "按周"}
    if any(kw in question for kw in group_time_kw) and num_cols:
        return "bar"

    # 4. 有日期列 + 有数值列 → 折线图（兜底：无明确意图默认趋势）
    if len(date_cols) >= 1 and len(num_cols) >= 1:
        return "line"

    # 5. 1~2 文本列 + ≥1 数值列 → 柱状图
    if 1 <= len(text_cols) <= 2 and len(num_cols) >= 1:
        return "bar"

    # 6. ≥2 数值列 → 散点图
    if len(num_cols) >= 2:
        return "scatter"

    # 7. 兜底 → 表格
    return "table"

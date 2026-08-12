"""
图表类型自动选择 —— 纯启发式规则。
不调 LLM：选图表是确定性问题，规则匹配就够了。
"""

from backend.schemas import ColumnMeta, ColumnType


def select(question: str, columns: list[ColumnMeta]) -> str:
    """根据用户问题和列类型，返回推荐的图表类型。

    Returns:
        "pie" | "line" | "bar" | "scatter" | "table"
    """
    col_names = [c.name for c in columns]
    col_types = {c.name: c.dtype for c in columns}

    text_cols = [n for n in col_names if col_types[n] == ColumnType.STRING]
    num_cols = [n for n in col_names if col_types[n] in (ColumnType.INTEGER, ColumnType.FLOAT)]
    date_cols = [n for n in col_names if col_types[n] == ColumnType.DATETIME]

    # 1. 问占比 + ≥1 文本列 + ≥1 数值列 → 饼图
    pie_kw = {"占比", "比例", "百分比", "分布", "份额", "比重", "构成"}
    if any(kw in question for kw in pie_kw) and text_cols and num_cols:
        return "pie"

    # 2. 问趋势 + 有日期列 → 折线图
    trend_kw = {"趋势", "变化", "走势", "增长", "下降", "随时间", "逐月", "逐日", "每日", "每月"}
    if any(kw in question for kw in trend_kw) and date_cols:
        return "line"

    # 3. 有日期列 + 有数值列 → 折线图
    if len(date_cols) >= 1 and len(num_cols) >= 1:
        return "line"

    # 4. 1~2 文本列 + ≥1 数值列 → 柱状图
    if 1 <= len(text_cols) <= 2 and len(num_cols) >= 1:
        return "bar"

    # 5. ≥2 数值列 → 散点图
    if len(num_cols) >= 2:
        return "scatter"

    # 6. 兜底 → 表格
    return "table"

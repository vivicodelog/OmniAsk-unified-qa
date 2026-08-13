from backend.chart_selector import select
from backend.util.infer_dtype import infer_dtype
from backend.schemas import ColumnMeta, ColumnType

# 快捷造列的函数（省得每个测试写一堆 ColumnMeta）
def _make_cols(*specs: tuple[str, ColumnType]) -> list[ColumnMeta]:
    return [ColumnMeta(name=n, dtype=t) for n, t in specs]


def test_pie():
    cols = _make_cols(("产品1", ColumnType.STRING), ("销量", ColumnType.FLOAT))
    sql = "SELECT 产品1, SUM(销量) FROM t GROUP BY 产品1"
    assert select("产品1占比是多少", cols, sql) == "pie"


def test_line():
    cols = _make_cols(("日期", ColumnType.DATETIME), ("产品1", ColumnType.STRING), ("销量", ColumnType.FLOAT))
    sql = "SELECT 日期, SUM(销量) FROM t GROUP BY 日期"
    assert select("产品1的销量趋势如何", cols, sql) == "line"


def test_bar():
    cols = _make_cols(("产品1", ColumnType.STRING), ("销量", ColumnType.FLOAT))
    sql = "SELECT 产品1, SUM(销量) FROM t GROUP BY 产品1"
    assert select("产品1的销量如何", cols, sql) == "bar"


def test_table():
    # 明细查询（无聚合）→ table
    cols = _make_cols(("产品1", ColumnType.STRING))
    sql = "SELECT DISTINCT 产品1 FROM t"
    assert select("产品种类是什么", cols, sql) == "table"


def test_line_default():
    """有日期+数值，没关键词 → 默认折线"""
    cols = _make_cols(("日期", ColumnType.DATETIME), ("销量", ColumnType.FLOAT))
    sql = "SELECT 日期, SUM(销量) FROM t GROUP BY 日期"
    assert select("看看数据", cols, sql) == "line"


def test_scatter():
    """无聚合，纯数值两列 → 相关性散点"""
    cols = _make_cols(("单价", ColumnType.FLOAT), ("销量", ColumnType.INTEGER))
    sql = "SELECT 单价, 销量 FROM t"
    assert select("看看相关性", cols, sql) == "scatter"


def test_bar_two_text():
    """两个文本+一个数值 → 柱状图"""
    cols = _make_cols(("区域", ColumnType.STRING), ("产品", ColumnType.STRING), ("销量", ColumnType.INTEGER))
    sql = "SELECT 区域, 产品, SUM(销量) FROM t GROUP BY 区域, 产品"
    assert select("各区域产品卖了多少", cols, sql) == "bar"


def test_group_by_month_is_bar():
    """各月销量（月份是日期）→ 柱状图，不是折线图"""
    cols = _make_cols(("月份", ColumnType.DATETIME), ("销量", ColumnType.FLOAT))
    sql = "SELECT 月份, SUM(销量) FROM t GROUP BY 月份"
    assert select("各月销量如何", cols, sql) == "bar"


def test_group_by_month_string_is_bar():
    """各月销量（月份是字符串）→ 柱状图（类型无关，结果一致）"""
    cols = _make_cols(("月份", ColumnType.STRING), ("销量", ColumnType.FLOAT))
    sql = "SELECT 月份, SUM(销量) FROM t GROUP BY 月份"
    assert select("各月销量如何", cols, sql) == "bar"


def test_trend_keyword_beats_group():
    """每月销量如何变化：趋势词优先 → 折线图"""
    cols = _make_cols(("月份", ColumnType.DATETIME), ("销量", ColumnType.FLOAT))
    sql = "SELECT 月份, SUM(销量) FROM t GROUP BY 月份"
    assert select("每月销量如何变化", cols, sql) == "line"


def test_detail_filter_is_table():
    """明细筛选（无聚合 + 结果列含日期）→ table，不被日期误判成 line"""
    cols = _make_cols(
        ("日期", ColumnType.DATETIME),
        ("地区", ColumnType.STRING),
        ("销售额", ColumnType.FLOAT),
    )
    sql = "SELECT * FROM t WHERE 是否退款 = 1"
    assert select("退款情况怎么样", cols, sql) == "table"


def test_column_name_not_matched_as_agg():
    """列名含 SUM/MIN 子串（如 CONSUMER）不应被正则误判为聚合"""
    cols = _make_cols(("CONSUMER", ColumnType.STRING))
    sql = "SELECT DISTINCT CONSUMER FROM t"
    assert select("消费者有哪些", cols, sql) == "table"


def test_infer_dtype():
    assert infer_dtype([8, 6, 12]) == ColumnType.INTEGER
    assert infer_dtype(["数码", "家电"]) == ColumnType.STRING
    assert infer_dtype([True, False, True]) == ColumnType.BOOLEAN
    assert infer_dtype([1.5, 2, 3.0]) == ColumnType.FLOAT
    assert infer_dtype([None, None]) == ColumnType.STRING

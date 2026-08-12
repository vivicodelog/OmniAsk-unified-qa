from backend.chart_selector import select
from backend.schemas import ColumnMeta, ColumnType

# 快捷造列的函数（省得每个测试写一堆 ColumnMeta）
def _make_cols(*specs: tuple[str, ColumnType]) -> list[ColumnMeta]:
    return [ColumnMeta(name=n, dtype=t) for n, t in specs]

def test_pie():
    cols = _make_cols(("产品1", ColumnType.STRING),("销量", ColumnType.FLOAT))
    assert select("产品1占比是多少", cols) == "pie"
def test_line():
    cols = _make_cols(("日期", ColumnType.DATETIME),("产品1", ColumnType.STRING),("销量", ColumnType.FLOAT))
    assert select("产品1的销量趋势如何", cols) == "line"

def test_bar():
    cols = _make_cols(("产品1", ColumnType.STRING),("销量", ColumnType.FLOAT))
    assert select("产品1的销量如何", cols) == "bar"
def test_table():
    cols = _make_cols(("产品1", ColumnType.STRING))
    assert select("产品种类是什么", cols) == "table"

def test_line_default():
    """有日期+数值，没关键词 → 默认折线"""
    cols = _make_cols(("日期", ColumnType.DATETIME), ("销量", ColumnType.FLOAT))
    assert select("看看数据", cols) == "line"

def test_scatter():
    """两个数值列，没文本没日期 → 散点"""
    cols = _make_cols(("单价", ColumnType.FLOAT), ("销量", ColumnType.INTEGER))
    assert select("看看相关性", cols) == "scatter"

def test_bar_two_text():
    """两个文本+一个数值 → 柱状图"""
    cols = _make_cols(("区域", ColumnType.STRING), ("产品", ColumnType.STRING), ("销量", ColumnType.INTEGER))
    assert select("各区域产品卖了多少", cols) == "bar"

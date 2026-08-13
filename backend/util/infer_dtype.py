from datetime import date, datetime
from decimal import Decimal

from backend.schemas import ColumnType

def infer_dtype(values: list) -> ColumnType:
    """聚合列无 schema 元数据，只能从结果值推断类型。"""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return ColumnType.STRING
    # bool 是 int 的子类，必须先判断，否则 True 会被误判成 INTEGER
    if all(isinstance(v, bool) for v in non_null):
        return ColumnType.BOOLEAN
    if all(isinstance(v, int) for v in non_null):
        return ColumnType.INTEGER
    if all(isinstance(v, (int, float, Decimal)) for v in non_null):
        return ColumnType.FLOAT
    if all(isinstance(v, (date, datetime)) for v in non_null):
        return ColumnType.DATETIME
    return ColumnType.STRING

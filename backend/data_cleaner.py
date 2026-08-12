"""数据清洗"""


from datetime import datetime

from backend.schemas import ColumnMeta, ColumnType

def clean_rows(records: list[dict], columns: list[ColumnMeta]) -> list[dict]:
    for record in records:
        for column in columns:
            if column.name not in record:
                continue
            cleaner = _CLEANERS.get(column.dtype)
            if cleaner:
                record[column.name] = cleaner(record[column.name])
    return records
def _to_datetime(v):
    if isinstance(v, str):
        return datetime.strptime(v, "%Y-%m-%d")
    return v  # 已经是 datetime 对象了，不动
TRUTHY = {"是", "true", "yes", True, 1, "1"}
def _to_bool(v):
    """把各种布尔表示统一转成 0 或 1。"""
    if isinstance(v, str):
       return 1 if v.strip().lower() in TRUTHY else 0
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int) and v in (0, 1):
        return v
    return 0  # 兜底

_CLEANERS = {
    ColumnType.DATETIME: _to_datetime,
    ColumnType.BOOLEAN: _to_bool,
    ColumnType.INTEGER: lambda v: int(v) if isinstance(v, str) else v,
    ColumnType.FLOAT: lambda v: float(v) if isinstance(v, str) else v
}
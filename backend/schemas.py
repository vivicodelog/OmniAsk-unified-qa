"""
Pydantic 数据模型 —— 统一的数据结构，前后端 + 内部模块都用这套。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# 列类型枚举
# ============================================================

class ColumnType(str, Enum):
    """列的数据类型 —— NL2SQL 生成 schema 的依据。"""
    INTEGER = "integer"
    FLOAT = "float"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    STRING = "string"


# ============================================================
# 列元数据
# ============================================================

class ColumnMeta(BaseModel):
    """单列的元信息：名称、类型、是否可空、唯一值数、样本值。"""
    name: str
    dtype: ColumnType
    nullable: bool = True
    unique_count: int = 0
    samples: list[Any] = Field(default_factory=list)


# ============================================================
# 解析结果
# ============================================================

class SheetInfo(BaseModel):
    """单个 sheet 的解析结果。"""
    name: str
    columns: list[ColumnMeta]
    records: list[dict[str, Any]]  # 每行是一个 dict，key 为列名
    row_count: int = 0

    def model_post_init(self, __context: Any) -> None:
        self.row_count = len(self.records)


class ParseResult(BaseModel):
    """一次文件解析的完整结果（可能包含多个 sheet）。"""
    file_name: str
    file_type: str  # "xlsx" | "csv" | "pdf"
    sheets: list[SheetInfo]
    total_rows: int = 0

    def model_post_init(self, __context: Any) -> None:
        self.total_rows = sum(s.row_count for s in self.sheets)


# ============================================================
# API 请求 / 响应（预留，Day 1 不用）
# ============================================================

class ChatRequest(BaseModel):
    session_id: str
    question: str
    file_id: str | None = None


class ChatChunk(BaseModel):
    """SSE 流式响应的单个 chunk。"""
    content: str = ""
    done: bool = False
    chart_type: str | None = None
    chart_data: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)

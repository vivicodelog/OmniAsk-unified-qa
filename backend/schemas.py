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
# PDF 解析结果（v2 多模态链路）
# ============================================================

class PdfTextBlock(BaseModel):
    """一段文本块 —— 供 text_retriever 转向量检索，供 SourceTrace 溯源高亮。"""
    page: int                                # 页码，统一 1-based（和 PDF 阅读器显示一致）
    text: str                                # 文本内容
    bbox: tuple[float, float, float, float]  # (x0,y0,x1,y1) 左上右下坐标，高亮的命门


class PdfTable(BaseModel):
    """一张表 —— 结构化数据，前端可直接渲染成 <table>。"""
    page: int
    bbox: tuple[float, float, float, float]
    rows: list[list[str]]  # 二维数组，第一行通常是表头


class PdfImage(BaseModel):
    """一张图片 —— 喂给 vision_agent（Qwen-VL）做看图问答。"""
    page: int
    bbox: tuple[float, float, float, float]
    data: bytes                              # 图片字节（PNG/JPEG），直接喂多模态 API
    ext: str                                 # 扩展名，写文件/存库时用


class PdfParseResult(BaseModel):
    """一次 PDF 解析的完整结果 —— 三类产出 + 元信息。"""
    file_name: str
    page_count: int = 0
    text_blocks: list[PdfTextBlock] = Field(default_factory=list)
    tables: list[PdfTable] = Field(default_factory=list)
    images: list[PdfImage] = Field(default_factory=list)
    
 
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

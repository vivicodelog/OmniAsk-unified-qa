"""
PDF 文件解析器 —— v2 多模态链路的入口。

职责：
1. 提取文本块（段落级，供 text_retriever 转向量检索）
2. 提取表格（pdfplumber，供结构化展示）
3. 提取图片（PyMuPDF，供 vision_agent 看图问答）

设计要点：
- 两个库分工：PyMuPDF 提文本 + 图片，pdfplumber 提表格
- page 统一 1-based（PyMuPDF 的 page.number 是 0-based，要 +1）
- bbox 统一 tuple[float, float, float, float]，是溯源高亮的依据
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, cast

import pdfplumber
import pymupdf  # PyMuPDF 新版导入名（fitz 已弃用）

from backend.schemas import PdfImage, PdfParseResult, PdfTable, PdfTextBlock


class PdfParser:
    """PDF 解析器 —— 无状态，纯函数式设计（和 ExcelParser 对齐）。"""

    @staticmethod
    def _extract_text(doc: pymupdf.Document) -> list[PdfTextBlock]:
        """提取文本块，过滤标题/图注（结构文本不进检索库）。

        用 get_text("dict") 而非 get_text("blocks")：只有 dict 模式能拿到 span 的字号，
        标题字号 > 正文，据此把「附录」「图表」这类结构文本挡在检索库外。
        """
        # 第一遍：收集 (page, text, bbox, size, is_bold, line_count) + 统计字号分布
        entries: list[tuple[int, str, tuple[float, float, float, float], float, bool, int]] = []
        size_counter: dict[float, int] = {}
        for page_idx, page in enumerate(cast(Iterable, doc)):
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:      # 只收文本块（0），图片块（1）留给 _extract_images
                    continue
                text, size, is_bold, line_count = PdfParser._scan_block(block)
                if not text.strip():
                    continue
                size_counter[size] = size_counter.get(size, 0) + len(text.strip())
                bbox = block["bbox"]
                entries.append((
                    page_idx + 1,               # enumerate 索引 +1 转 1-based
                    text.strip(),
                    (bbox[0], bbox[1], bbox[2], bbox[3]),
                    size,
                    is_bold,
                    line_count,
                ))
        if not entries:
            return []
        body_size = max(size_counter, key=size_counter.get)   # 正文字号 = 字符最多的字号

        blocks: list[PdfTextBlock] = []
        for page, text, bbox, size, is_bold, line_count in entries:
            if PdfParser._is_heading(size, body_size, is_bold, line_count):
                continue      # 标题/图注是结构文本，不是正文内容，不进检索库
            blocks.append(PdfTextBlock(page=page, text=text, bbox=bbox))
        return blocks

    @staticmethod
    def _scan_block(block: dict) -> tuple[str, float, bool, int]:
        """扫一个 dict block：拼回文本 + 主导字号 + 是否加粗 + 行数（一次遍历）。"""
        lines: list[str] = []
        size_counter: dict[float, int] = {}
        is_bold = False
        for line in block.get("lines", []):
            line_text = ""
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text:
                    line_text += text
                    size = span.get("size", 0.0)
                    size_counter[size] = size_counter.get(size, 0) + len(text)
                    if span.get("flags", 0) & 16:   # flags bit4=16 表示 bold
                        is_bold = True
            lines.append(line_text)
        text = "\n".join(lines)
        size = max(size_counter, key=size_counter.get) if size_counter else 0.0
        return text, size, is_bold, len(lines)

    @staticmethod
    def _is_heading(size: float, body_size: float, is_bold: bool, line_count: int) -> bool:
        """标题/图注判定：字号明显大于正文，或单行加粗（典型标题排版）。"""
        return size > body_size * 1.15 or (is_bold and line_count == 1)

    @staticmethod
    def _extract_tables(path: Path) -> list[PdfTable]:
        tables: list[PdfTable] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                for table in page.find_tables():
                    raw = table.extract()
                    rows = [[cell if cell is not None else "" for cell in row] for row in raw]
                    tables.append(PdfTable(
                        page=page.page_number,       # 1-based，不用 +1
                        bbox=cast(tuple[float, float, float, float], table.bbox),
                        rows=rows,
                    ))
        return tables

    
    @staticmethod
    def _extract_images(doc: pymupdf.Document) -> list[PdfImage]:
        images: list[PdfImage] = []
        for page_idx, page in enumerate(cast(Iterable, doc)):
            for img in page.get_images(full=True):       # ① 这页引用了哪些图片
                xref = img[0]                             # 图片的资源 ID（xref）
                info = doc.extract_image(xref)            # ② 按 ID 掏图片字节
                data = info["image"]                      # 图片字节（bytes）
                ext = info["ext"]                         # 扩展名（"png"/"jpeg"）
                for rect in page.get_image_rects(xref):   # ③ 图片在页面的位置
                    images.append(PdfImage(
                        page=page_idx + 1,    # enumerate 索引 +1 转 1-based
                        bbox=(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)),
                        data=data,
                        ext=ext,
                    ))
        return images
    
    
    @staticmethod
    def parse(path: str | Path) -> PdfParseResult:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")

        doc = pymupdf.open(path)            # PyMuPDF 打开一次
        page_count = doc.page_count         # 总页数（close 之前取！）
        text_blocks = PdfParser._extract_text(doc)    # ① 文本
        images = PdfParser._extract_images(doc)       # ② 图片
        doc.close()                          # PyMuPDF 用完关闭

        tables = PdfParser._extract_tables(path)      # ③ 表格（pdfplumber 自己开文件）

        return PdfParseResult(
            file_name=path.name,
            page_count=page_count,
            text_blocks=text_blocks,
            tables=tables,
            images=images,
        )

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
        """遍历每一页，把文本块转成 PdfTextBlock。"""
        blocks: list[PdfTextBlock] = []
        for page_idx, page in enumerate(cast(Iterable, doc)):
            for x0, y0, x1, y1, text, _block_no, block_type in page.get_text("blocks"):
                if block_type != 0:      # 只收文本块（0），图片块（1）留给 _extract_images
                    continue
                if not text.strip():     # 空块跳过，别让垃圾进向量库
                    continue
                blocks.append(PdfTextBlock(
                    page=page_idx + 1,    # enumerate 索引 +1 转 1-based
                    text=text.strip(),
                    bbox=(x0, y0, x1, y1),
                ))
        return blocks

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

"""测试 pdf文档的text table image提取"""

"""测试 PdfParser —— 文本 / 图片 / 表格三类提取 + parse 组装。"""

import pytest

from backend.parsers.pdf_parser import PdfParser
from backend.schemas import PdfParseResult


class TestPdfParser:
    """PDF 解析测试（测试 PDF 由 conftest 的 sample_pdf_path 现场生成）。"""

    def test_parse_returns_result(self, sample_pdf_path: str):
        """parse 组装：返回 PdfParseResult，元信息正确。"""
        result = PdfParser.parse(sample_pdf_path)

        assert isinstance(result, PdfParseResult)
        assert result.page_count == 1
        assert result.file_name.endswith(".pdf")

    def test_extract_text(self, sample_pdf_path: str):
        """文本提取：能拿到含中文的文本块。"""
        result = PdfParser.parse(sample_pdf_path)

        assert len(result.text_blocks) >= 1
        all_text = "".join(b.text for b in result.text_blocks)
        assert "测试" in all_text

    def test_extract_images(self, sample_pdf_path: str):
        """图片提取：能拿到图片字节 + 扩展名 + 页码。"""
        result = PdfParser.parse(sample_pdf_path)

        assert len(result.images) >= 1
        img = result.images[0]
        assert isinstance(img.data, bytes)
        assert img.ext == "png"
        assert img.page == 1

    def test_no_tables_in_plain_pdf(self, sample_pdf_path: str):
        """简单 PDF（无边框表格）→ tables 为空。"""
        result = PdfParser.parse(sample_pdf_path)

        assert result.tables == []

    def test_file_not_found(self):
        """文件不存在时抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            PdfParser.parse("nonexistent_file.pdf")

    def test_is_heading_judgment(self):
        """标题判定：字号大、或单行加粗 → 标题；正文/多行加粗 → 不是。"""
        assert PdfParser._is_heading(14.0, 10.0, False, 3) is True   # 字号明显大
        assert PdfParser._is_heading(10.0, 10.0, True, 1) is True    # 单行加粗
        assert PdfParser._is_heading(10.0, 10.0, False, 3) is False  # 正文
        assert PdfParser._is_heading(10.0, 10.0, True, 3) is False   # 多行加粗

    def test_extract_text_filters_heading(self, tmp_path):
        """标题（大字号）被过滤，正文（正文字号）保留。"""
        import pymupdf
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "附录：各产品线明细", fontname="china-s", fontsize=16)
        page.insert_text((72, 120), "这是正文内容测试文本", fontname="china-s", fontsize=11)
        path = tmp_path / "heading.pdf"
        doc.save(str(path))
        doc.close()

        result = PdfParser.parse(str(path))
        texts = [b.text for b in result.text_blocks]
        assert any("正文" in t for t in texts)
        assert not any("附录" in t for t in texts)

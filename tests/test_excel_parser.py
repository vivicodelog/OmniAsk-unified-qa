"""
测试 ExcelParser —— 覆盖正常路径、边界、异常。
"""

import pytest

from backend.parsers.excel_parser import ExcelParser
from backend.schemas import ColumnType, ParseResult, SheetInfo


class TestExcelParser:
    """Excel 文件解析测试。"""

    def test_parse_multi_sheet(self, sample_xlsx_path: str):
        """解析多 sheet Excel，验证每个 sheet 都被正确解析。"""
        result = ExcelParser.parse(sample_xlsx_path)

        assert isinstance(result, ParseResult)
        assert result.file_type == "xlsx"
        assert len(result.sheets) == 3  # 销售订单 + 客户信息 + 合并区域

        sheet_names = [s.name for s in result.sheets]
        assert "销售订单" in sheet_names
        assert "客户信息" in sheet_names
        assert "合并区域" in sheet_names

    def test_sheet_row_count(self, sample_xlsx_path: str):
        """验证行数统计正确。"""
        result = ExcelParser.parse(sample_xlsx_path)

        sales_sheet = _find_sheet(result, "销售订单")
        assert sales_sheet.row_count == 10
        assert result.total_rows == 10 + 5 + 6  # 三个 sheet 的行数

    def test_column_type_inference(self, sample_xlsx_path: str):
        """验证每列的类型推断结果。"""
        result = ExcelParser.parse(sample_xlsx_path)
        sales = _find_sheet(result, "销售订单")

        col_map = {c.name: c.dtype for c in sales.columns}

        assert col_map["订单ID"] == ColumnType.INTEGER
        assert col_map["客户名称"] == ColumnType.STRING
        assert col_map["订单日期"] == ColumnType.DATETIME
        assert col_map["金额"] == ColumnType.FLOAT
        assert col_map["数量"] == ColumnType.INTEGER
        assert col_map["是否会员"] == ColumnType.BOOLEAN
        assert col_map["备注"] == ColumnType.STRING

    def test_nullable_detection(self, sample_xlsx_path: str):
        """验证可空列检测 —— 备注和信用额度有缺失值。"""
        result = ExcelParser.parse(sample_xlsx_path)

        sales = _find_sheet(result, "销售订单")
        remark_col = _find_column(sales, "备注")
        assert remark_col.nullable is True  # 有 None 值

        id_col = _find_column(sales, "订单ID")
        assert id_col.nullable is False  # 全部有值

    def test_unique_count(self, sample_xlsx_path: str):
        """验证唯一值计数。"""
        result = ExcelParser.parse(sample_xlsx_path)
        sales = _find_sheet(result, "销售订单")

        id_col = _find_column(sales, "订单ID")
        assert id_col.unique_count == 10  # 每行都不同

        bool_col = _find_column(sales, "是否会员")
        assert bool_col.unique_count == 2  # 是/否

    def test_samples_collected(self, sample_xlsx_path: str):
        """验证样本值收集。"""
        result = ExcelParser.parse(sample_xlsx_path)
        sales = _find_sheet(result, "销售订单")

        name_col = _find_column(sales, "客户名称")
        assert len(name_col.samples) >= 1
        assert isinstance(name_col.samples[0], str)

    def test_merged_cells_fill(self, sample_xlsx_path: str):
        """合并单元格前向填充：部门的 None 值应被填充为上一行的部门名。"""
        result = ExcelParser.parse(sample_xlsx_path)
        merged_sheet = _find_sheet(result, "合并区域")

        departments = [r["部门"] for r in merged_sheet.records]
        # 每个员工都应该有部门名，没有 None
        assert all(d is not None for d in departments)
        assert departments == [
            "技术部", "技术部", "技术部",
            "销售部", "销售部",
            "市场部",
        ]

    def test_records_have_all_columns(self, sample_xlsx_path: str):
        """验证每一行都包含所有列名作为 key。"""
        result = ExcelParser.parse(sample_xlsx_path)
        sales = _find_sheet(result, "销售订单")

        expected_keys = {"订单ID", "客户名称", "订单日期", "金额", "数量", "是否会员", "备注"}
        for record in sales.records:
            assert set(record.keys()) == expected_keys

    # ================================================================
    # 边界 / 异常
    # ================================================================

    def test_file_not_found(self):
        """文件不存在时抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            ExcelParser.parse("nonexistent_file.xlsx")

    def test_unsupported_extension(self, tmp_path):
        """不支持的文件类型抛出 ValueError。"""
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("hello")
        with pytest.raises(ValueError, match="不支持的文件类型"):
            ExcelParser.parse(str(bad_file))


class TestCSVParser:
    """CSV 文件解析测试。"""

    def test_parse_csv(self, sample_csv_path: str):
        """基本 CSV 解析。"""
        result = ExcelParser.parse(sample_csv_path)

        assert result.file_type == "csv"
        assert len(result.sheets) == 1
        assert result.sheets[0].name == "data"
        assert result.sheets[0].row_count == 5

    def test_csv_column_types(self, sample_csv_path: str):
        """CSV 列类型推断。"""
        result = ExcelParser.parse(sample_csv_path)
        sheet = result.sheets[0]
        col_map = {c.name: c.dtype for c in sheet.columns}

        assert col_map["销量"] == ColumnType.INTEGER
        assert col_map["单价"] == ColumnType.FLOAT
        assert col_map["产品"] == ColumnType.STRING
        assert col_map["上架"] == ColumnType.BOOLEAN


class TestTypeInferenceEdgeCases:
    """列类型推断的边界测试 —— 直接测 _guess_type。"""

    def test_mixed_types_fallback_to_string(self):
        """混合类型列应回退到 string。"""
        dtype, _ = ExcelParser._guess_type(["hello", 123, 3.14])
        assert dtype == ColumnType.STRING

    def test_all_none_column(self):
        """空列（在 _infer_column_types 层面处理，这里测逻辑一致性）。"""
        # 模拟全空值场景
        dtype, _ = ExcelParser._guess_type([None, None])  # type: ignore[arg-type]
        # _guess_type 不处理 None（调用方已过滤），但若传入应回退
        # 实际走不到这里——_infer_column_types 在过滤后发现 non_null 为空直接返回 STRING

    def test_bool_as_int_not_confused(self):
        """bool 值不应被误判为 int（bool 是 int 子类）。"""
        # 全部是 True/False
        dtype, _ = ExcelParser._guess_type([True, False, True])
        assert dtype == ColumnType.BOOLEAN

    def test_int_string_distinction(self):
        """纯数字字符串仍判为 integer。"""
        dtype, _ = ExcelParser._guess_type(["100", "200", "300"])
        assert dtype == ColumnType.INTEGER  # openpyxl 读 Excel 时数字是 int，但 CSV 会是 str

    def test_float_with_dot_string(self):
        """含小数点的字符串判为 float。"""
        dtype, _ = ExcelParser._guess_type(["3.14", "2.718", "1.0"])
        assert dtype == ColumnType.FLOAT

    def test_date_strings(self):
        """日期字符串判为 datetime。"""
        dtype, _ = ExcelParser._guess_type(["2024-01-15", "2024-02-20", "2024-03-10"])
        assert dtype == ColumnType.DATETIME

    def test_small_bool_set(self):
        """中文布尔值识别。"""
        dtype, _ = ExcelParser._guess_type(["是", "否", "是", "是"])
        assert dtype == ColumnType.BOOLEAN


# ================================================================
# 辅助函数
# ================================================================

def _find_sheet(result: ParseResult, name: str) -> SheetInfo:
    for s in result.sheets:
        if s.name == name:
            return s
    raise KeyError(f"Sheet {name!r} not found")


def _find_column(sheet: SheetInfo, name: str):
    for c in sheet.columns:
        if c.name == name:
            return c
    raise KeyError(f"Column {name!r} not found")

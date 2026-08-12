

import pytest

from backend.file_router import _new_session, get_session, route
from backend.schemas import ColumnType


class TestSession:
    """会话管理器。"""
    def test_session(self):
        sid, ctx = _new_session()
        assert len(sid) == 12
        assert ctx.db is not None
    def test_get_session(self) -> str|None:
        sid, ctx = _new_session()
        assert get_session(sid) is ctx
        assert get_session("不存在的ID") is None
    

class TestFileRouter:
    """文件路由。"""
    def test_upload_xlsx(self) -> str|None:
        new_session_id, _ = _new_session()
        result = route("data/sample_sales.xlsx", new_session_id)
        assert result[0].file_type == "xlsx"
    def test_upload_csv(self) -> str|None:
        new_session_id, _ = _new_session()
        result = route("data/sample_sales.csv", new_session_id)
        assert result[0].file_type == "csv"
    def test_upload_pdf(self) -> str|None:
        with pytest.raises(ValueError, match="PDF 解析暂未实现"):
            route("xxx.pdf")
    def test_upload_unknown(self) -> str|None:
        with pytest.raises(ValueError, match="不支持的文件类型"):
            route("xxx.txt")           
    def test_same_file(self) -> str|None:
        new_session_id, _ = _new_session()
        with pytest.raises(ValueError, match="该文件已上传过"):
            route("data/sample_sales.xlsx", new_session_id)
            route("data/sample_sales.xlsx", new_session_id)
    def test_file_not_exists(self) -> str|None:
        new_session_id, _ = _new_session()
        with pytest.raises(FileNotFoundError):
            route("data/file_not_exists.xlsx", new_session_id)

    def test_session_id(self) -> str|None:
        result, sid = route("data/sample_sales.xlsx")
        ctx = get_session(sid) 
        assert ctx is not None
    def test_columns(self):
        result, sid = route("data/sample_sales.xlsx")
        assert result.sheets[0].columns[0].dtype == ColumnType.DATETIME
        assert result.sheets[0].columns[0].name == "日期"

    
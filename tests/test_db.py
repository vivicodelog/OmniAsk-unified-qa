"""测试 DBManager —— 需要本地 MySQL 运行。"""
import pytest
from backend.db import DBManager
from backend.config import MYSQL_CONFIG
from backend.schemas import ColumnMeta, ColumnType

DB_NAME = MYSQL_CONFIG["database"]


@pytest.fixture
def db():
    """每个测试用例一个 DBManager 实例，测试结束自动关连接。"""
    mgr = DBManager()
    yield mgr
    mgr.close()


class TestCreateTable:
    """建表验证。"""
    
    TABLE = "test_create_table"
    
    @pytest.fixture(autouse=True)
    def cleanup(self, db):
        """测试前后清理：确保没有残留表。"""
        db.drop_table(self.TABLE)
        yield
        db.drop_table(self.TABLE)
    
    def test_columns_and_types(self, db):
        """建表后查 INFORMATION_SCHEMA，验证列名和类型映射。"""
        columns = [
            ColumnMeta(name="序号", dtype=ColumnType.INTEGER, nullable=False),
            ColumnMeta(name="名称", dtype=ColumnType.STRING, nullable=True),
            ColumnMeta(name="价格", dtype=ColumnType.FLOAT, nullable=True),
            ColumnMeta(name="日期", dtype=ColumnType.DATETIME, nullable=True),
            ColumnMeta(name="上架", dtype=ColumnType.BOOLEAN, nullable=True),
        ]
        
        db.create_table(self.TABLE, columns)
        
        # 查 INFORMATION_SCHEMA 拿真实列信息
        db.cursor.execute(
            "SELECT COLUMN_NAME, DATA_TYPE "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION",
            (DB_NAME, self.TABLE)
        )
        result = db.cursor.fetchall()
        
        assert len(result) == 5
        assert result[0] == {"COLUMN_NAME": "序号", "DATA_TYPE": "bigint"}
        assert result[1] == {"COLUMN_NAME": "名称", "DATA_TYPE": "varchar"}
        assert result[2] == {"COLUMN_NAME": "价格", "DATA_TYPE": "double"}
        assert result[3] == {"COLUMN_NAME": "日期", "DATA_TYPE": "datetime"}
        assert result[4] == {"COLUMN_NAME": "上架", "DATA_TYPE": "tinyint"}

class TestInsertRows: 
    """插入数据验证。"""
    TABLE = "test_insert_rows"
    @pytest.fixture(autouse=True)
    def setup(self, db):
        """建表 → 测试 → 清理。"""
        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER),
            ColumnMeta(name="name", dtype=ColumnType.STRING),
        ]
        db.create_table(self.TABLE, columns)
        yield
        db.drop_table(self.TABLE)
    def test_insert_and_count(self, db):
        """插入 3 行，SELECT COUNT(*) 应该返回 3。"""
        rows = [
            {"id": 1, "name": "张三"},
            {"id": 2, "name": "李四"},
            {"id": 3, "name": "王五"},
        ]
        db.insert_rows(self.TABLE, rows)
        
        db.cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{self.TABLE}`")
        result = db.cursor.fetchone()
        assert result["cnt"] == 3

class TestQuery:
    """查询数据验证。"""
    TABLE = "test_query"
    @pytest.fixture(autouse=True)
    def setup(self, db):
        """建表 → 测试 → 清理。"""
        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER),
            ColumnMeta(name="name", dtype=ColumnType.STRING),
        ]
        db.create_table(self.TABLE, columns)
        yield
        db.drop_table(self.TABLE)
    def test_query(self, db):
        """插入 3 行，SELECT * 应该返回 3 行。"""
        rows = [
            {"id": 1, "name": "张三"},
            {"id": 2, "name": "李四"},
            {"id": 3, "name": "王五"},
        ]
        db.insert_rows(self.TABLE, rows)
        result = db.query(self.TABLE, columns=["id", "name"])
        assert len(result) == 3
        assert result[0] == {"id": 1, "name": "张三"}
    def test_query_all_columns(self, db):
        """SELECT * 返回所有列。"""
        rows = [{"id": 1, "name": "张三"}]
        db.insert_rows(self.TABLE, rows)
        result = db.query(self.TABLE)
        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "张三"}

class TestClose:
    def test_close_connection(self, db):
        """close() 后连接标记为关闭。"""
        db = DBManager()
        assert db.conn.open is True          # 初始是开的
        db.close()
        assert db.conn.open is False         # 关了就变 False

class TestDropTable:
    """删除表验证。"""
    TABLE = "test_drop_table"
    @pytest.fixture(autouse=True)
    def setup(self, db):
        """建表 → 测试 → 清理。"""
        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER),
            ColumnMeta(name="name", dtype=ColumnType.STRING),
        ]
        db.create_table(self.TABLE, columns)
        yield
        db.drop_table(self.TABLE)
    def test_drop_table(self, db):
        """删表后 INFORMATION_SCHEMA 里查不到。"""
        db.drop_table(self.TABLE)

        db.cursor.execute(
            "SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (DB_NAME, self.TABLE)
        )
        result = db.cursor.fetchone()
        assert result["cnt"] == 0


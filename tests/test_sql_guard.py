"""
测试 SQL 防护。
"""

import pytest
from backend.sql_guard import SQLGuard


@pytest.fixture
def guard():
    g = SQLGuard()
    g.register_table("orders")
    return g


class TestSqlGuard:
    """sql guard 测试。"""

    def test_normal_select(self, guard):
        ok, msg = guard.validate("SELECT * FROM orders")
        assert ok is True
        assert msg == "OK"   
    def test_check_select_only(self):
        """只允许SELECT查询。"""
        sql = "SELECT * FROM orders JOIN customers ON orders.cid = customers.id"
        result = SQLGuard._check_select_only(sql)
        assert result == (True, "OK")
    def test_check_select_only_lower(self):
        """只允许SELECT查询。"""
        sql = "select * FROM orders JOIN customers ON orders.cid = customers.id"
        result = SQLGuard._check_select_only(sql)
        assert result == (True, "OK")
    
    def test_check_non_select(self):
        """只允许SELECT查询。"""
        sql = "	DROP TABLE orders"
        result = SQLGuard._check_select_only(sql)
        assert result == (False, "只允许 SELECT 查询")
    
    def test_check_single_statement(self):
        """不允许多语句"""
        sql = "SELECT * FROM t; DROP TABLE t"
        result = SQLGuard._check_single_statement(sql)
        assert result == (False, "不允许多语句")
    def test_check_single_statement_inner(self):
        """引号内分号不拦截"""
        sql = "SELECT * FROM t WHERE name = '张三;李四' AND age > 18"
        ok, msg = SQLGuard._check_single_statement(sql)
        assert ok is True
    
    def test_check_table_whitelist(self,guard):
        """不允许查询表"""  
        ok, msg = guard._check_table_whitelist("SELECT * FROM users")
        assert ok is False

    def test_check_union(self,guard):
        """运行UNION 查询""" 
        sql = "SELECT * FROM orders UNION SELECT 'hacker', 123, 'fake_data'"
        ok, msg = guard._check_union(sql)
        assert ok is False
    def test_check_union_all_allowed(self, guard):
        """两张表都在白名单"""
        sql = "SELECT * FROM orders UNION SELECT * FROM orders"
        ok, msg = guard._check_union(sql)
        assert ok is True

    def test_check_union_one_rejected(self, guard):
        """一张表不在白名单"""
        sql = "SELECT * FROM orders UNION SELECT * FROM goods"
        ok, msg = guard._check_union(sql)
        assert ok is False

    def test_register_table(self):
        g = SQLGuard()
        g.register_table("orders")
        assert "orders" in g.allowed_tables

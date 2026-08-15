from unittest.mock import patch
from typing import cast

import pytest

from backend.agents.nl2sql_agent import NL2SQLAgent
from backend.db import DBManager
from backend.schemas import ColumnMeta, ColumnType
from backend.sql_guard import SQLGuard

class TestExtractSql:
    def test_pure_sql(self):
        sql = NL2SQLAgent._extract_sql("SELECT * FROM table WHERE id = 1;")
        assert sql == "SELECT * FROM table WHERE id = 1;"
    def test_markdown_block(self):
        """抠出 ```sql ... ``` 里面的内容"""
        sql = NL2SQLAgent._extract_sql("""
```sql
SELECT * FROM table WHERE id = 1;
```
""")
        assert sql == "SELECT * FROM table WHERE id = 1;"


    def test_prefix_removal(self):
        """去掉"这是查询："前缀"""
        sql = NL2SQLAgent._extract_sql("这是查询：SELECT * FROM table WHERE id = 1;")
        assert sql == "SELECT * FROM table WHERE id = 1;"

    def test_trailing_junk(self):
        """分号后面的尾巴裁掉"""
        sql = NL2SQLAgent._extract_sql("SELECT * FROM table WHERE id = 1; 尾随内容")
        assert sql == "SELECT * FROM table WHERE id = 1;"

@pytest.fixture
def db():
    mgr = DBManager()
    yield mgr
    mgr.close()

@pytest.fixture
def guard():
    g = SQLGuard()
    g.register_table("people")
    return g

class TestRunWithMock:
    TABLE = "people"
    @pytest.fixture(autouse=True)
    def setup(self, db):
        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER),
            ColumnMeta(name="name", dtype=ColumnType.STRING),
            ColumnMeta(name="city", dtype=ColumnType.STRING),
        ]
        db.create_table(self.TABLE, columns)
        db.insert_rows(self.TABLE, [{"id": 1, "name": "Alice", "city": "New York"}])
        yield
        db.drop_table(self.TABLE)
    def test_run_with_mock(self, db, guard):
        agent = NL2SQLAgent()
        question = "查找所有在纽约的人的名字"
        schema = """表 people（id BIGINT, name VARCHAR, city VARCHAR）"""
        with patch.object(agent, '_call_llm', return_value="SELECT name FROM people WHERE city = 'New York'"):
            result = agent.run(question, schema, db, guard)
            assert result["success"] is True
            assert result["sql"] == "SELECT name FROM people WHERE city = 'New York'"
    def test_run_with_mock_retry(self, db, guard):
        agent = NL2SQLAgent()
        question = "查找所有在纽约的人的名字"
        schema = """表 people（id BIGINT, name VARCHAR, city VARCHAR）"""
        with patch.object(agent, '_call_llm', side_effect=[
            "SELECT name FROM people city = 'New York'",
            "SELECT name FROM people wheWHEREre city = 'New York'",
             "SELECT name FROM people WHERE city = 'New York'",]):
            result = agent.run(question, schema, db, guard)
            assert result["success"] is True
    def test_run_with_error(self, db, guard):
        agent = NL2SQLAgent()
        question = "查找所有在纽约的人的名字"
        schema = """表 people（id BIGINT, name VARCHAR, city VARCHAR）"""
        with patch.object(agent, '_call_llm', return_value="DELETE FROM people"):           
            result = agent.run(question, schema, db, guard)
            assert result["success"] is False
            assert "SQL 生成或执行重试 3 次仍失败" in result["error"]

    def test_run_with_llm_except(self, db, guard):
        agent = NL2SQLAgent()
        question = "查找所有在纽约的人的名字"
        schema = """表 people（id BIGINT, name VARCHAR, city VARCHAR）"""
        with patch.object(agent, '_call_llm', side_effect=RuntimeError()):
            result = agent.run(question, schema, db, guard)
            assert result["success"] is False  
    def test_run_with_mock_error(self, db, guard):
        agent = NL2SQLAgent()
        question = "查找所有在纽约的人的名字"
        schema = """表 people（id BIGINT, name VARCHAR, city VARCHAR）"""
        with patch.object(agent, '_call_llm', return_value="SELECT wrong_column FROM people"):
            result = agent.run(question, schema, db, guard)
            assert result["success"] is False
    def test_run_retry_after_guard_fail(self, db, guard):
        agent = NL2SQLAgent()
        question = "查找所有在纽约的人的名字"
        schema = """表 people（id BIGINT, name VARCHAR, city VARCHAR）"""
        with patch.object(agent, '_call_llm', side_effect=[
            "DELETE FROM people",                                  # 校验失败
            "SELECT name FROM people WHERE city = 'New York'",    # 校验通过 + 执行成功
        ]):
            result = agent.run(question, schema, db, guard)
            assert result["success"] is True
            assert result["sql"] == "SELECT name FROM people WHERE city = 'New York'"

class TestSummarize:
    def test_empty(self):
        assert NL2SQLAgent._summarize([]) == "空结果"
    def test_small(self):
        assert NL2SQLAgent._summarize([{"a": 1}, {"a": 2}]) == "[{'a': 1}, {'a': 2}]"
    def test_large(self):
        rows = [{"a": i} for i in range(15)]
        out = NL2SQLAgent._summarize(rows)
        assert "共 15 行" in out and "..." in out

class TestHistory:
    TABLE = "people"

    @pytest.fixture(autouse=True)
    def setup(self, db):
        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER),
            ColumnMeta(name="name", dtype=ColumnType.STRING),
            ColumnMeta(name="city", dtype=ColumnType.STRING),
        ]
        db.create_table(self.TABLE, columns)
        db.insert_rows(self.TABLE, [{"id": 1, "name": "Alice", "city": "New York"}])
        yield
        db.drop_table(self.TABLE)
    def test_appended_after_run(self, db, guard):
        agent = NL2SQLAgent()
        with patch.object(agent, '_call_llm', return_value="SELECT name FROM people WHERE city = 'New York'"):
            agent.run("查找纽约的人", "表 people(...)", db, guard)
            assert len(agent.history) == 2
    def test_trimmed_to_5_turns(self, db, guard):
        agent = NL2SQLAgent()
        with patch.object(agent, '_call_llm', return_value="SELECT name FROM people WHERE city = 'New York'"):
            for i in range(6):
                agent.run(f"问题{i}", "表 people(...)", db, guard)
            assert len(agent.history) == 10   # 5 轮 × 2 条

class TestClarify:
    def test_need_clarify(self, db, guard):
        agent = NL2SQLAgent()
        with patch.object(agent, '_call_llm', return_value="需要澄清：你指的是哪个产品？"):
            result = agent.run("那它的库存呢", "表 people(...)", db, guard)
            assert result["success"] is False
            assert result["need_clarify"] is True
            assert result["question"] == "你指的是哪个产品？"
    def test_clarify_recorded_in_history(self, db, guard):
        agent = NL2SQLAgent()
        with patch.object(agent, '_call_llm', return_value="需要澄清：你指的是哪个？"):
            agent.run("那它的库存呢", "表 people(...)", db, guard)
            assert any(cast(str, m.get("content")).startswith("需要澄清") for m in agent.history)

"""
SQL 安全校验 —— 白名单机制。
只允许对已注册的临时表执行只读查询。
"""

import re
from dataclasses import dataclass, field

# 表名可能被反引号包裹（如 `qa_0`），\w 匹配不到反引号，需专门处理
_TABLE_RE = re.compile(r"(?:FROM|JOIN)\s+(?:`([^`]+)`|([^\s`]+))", re.IGNORECASE)


@dataclass
class SQLGuard:
    """SQL 安全校验器。每个会话创建一个实例，注册自己的表。"""

    allowed_tables: set[str] = field(default_factory=set)

    # ---------- 公开方法 ----------

    def register_table(self, table_name: str) -> None:
        """注册一个允许查询的表名。"""
        self.allowed_tables.add(table_name)

    def validate(self, sql: str) -> tuple[bool, str]:
        """校验 SQL 是否安全。返回 (通过, 原因)。"""
        sql = sql.strip()

        # 1. 非空
        if not sql:
            return False, "SQL 为空"

        # 2. 必须 SELECT 开头
        ok, reason = self._check_select_only(sql)
        if not ok:
            return False, reason

        # 3. 多语句检测
        ok, reason = self._check_single_statement(sql)
        if not ok:
            return False, reason

        # 4. 表名白名单
        ok, reason = self._check_table_whitelist(sql)
        if not ok:
            return False, reason

        # 5. 禁止 UNION（暂时）
        ok, reason = self._check_union(sql)
        if not ok:
            return False, reason

        return True, "OK"

    @staticmethod
    def _check_select_only(sql: str) -> tuple[bool, str]:
        upper = sql.upper().lstrip()
        if not upper.startswith("SELECT "):
            return False, "只允许 SELECT 查询"
        return True, "OK"

    @staticmethod
    def _check_single_statement(sql: str) -> tuple[bool, str]:
        in_quote = False
        # 遇到引号翻转标记，遇到分号且标记为 False 就拦截
        for char in sql:
            if char == "'" or char == '"':
                in_quote = not in_quote
            if char == ';' and not in_quote:
                return False, "不允许多语句"
        return True, "OK"

    @staticmethod
    def _extract_tables(sql: str) -> list[str]:
        """提取 FROM/JOIN 后的表名，支持反引号包裹（如 `qa_0`）。"""
        return [a or b for a, b in _TABLE_RE.findall(sql)]

    def _check_table_whitelist(self, sql: str) -> tuple[bool, str]:
        for table_name in self._extract_tables(sql):
            if table_name not in self.allowed_tables:
                return False, f"不允许查询表 {table_name}"
        return True, "OK"


    def _check_union(self, sql: str) -> tuple[bool, str]:
        parts = re.split(r'\bUNION\b', sql, flags=re.IGNORECASE)#正则表达式永远加 r
        for i, part in enumerate(parts):
            tables = self._extract_tables(part)
            if not tables:
                return False, f"第 {i+1} 段 SELECT 缺少表名"
            for t in tables:
                if t not in self.allowed_tables:
                    return False, f"表 {t} 不在白名单"
        return True, "OK"














"""
数据库管理
"""
import pymysql  
from backend.config import MYSQL_CONFIG

from backend.schemas import ColumnMeta, ColumnType


_TYPE_MAP = {
    ColumnType.INTEGER: "BIGINT",
    ColumnType.FLOAT: "DOUBLE",
    ColumnType.DATETIME: "DATETIME",
    ColumnType.BOOLEAN: "TINYINT(1)",
    ColumnType.STRING: "VARCHAR(512)",
}

class DBManager:
    def __init__(self):
        self.conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        self.cursor = self.conn.cursor()

    def create_table(self, table_name: str, columns: list[ColumnMeta]) -> None:
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ("
        sql += ", ".join(
            [
                f"`{column.name}` {_TYPE_MAP[column.dtype]}"
                for column in columns
            ]
        ) + ")"
        self.cursor.execute(sql)
        self.conn.commit()
    def insert_rows(self, table_name: str, rows: list[dict]) -> None:
        if not rows: return
        columns = rows[0].keys()
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ("
        sql += ", ".join(["%s"] * len(columns))
        sql += ")"
        self.cursor.executemany(sql, [tuple(row.values()) for row in rows])
        self.conn.commit()

    def query(self, table_name: str, columns: list[str] | None = None) -> list[dict]:
        sql = f"SELECT {', '.join(columns) if columns else '*'} FROM {table_name}"
        self.cursor.execute(sql)
        return self.cursor.fetchall()
    
    def drop_table(self, table_name: str) -> None:
        sql = f"DROP TABLE IF EXISTS {table_name}"
        self.cursor.execute(sql)
    def close(self) -> None:
        self.conn.commit()
        self.conn.close()



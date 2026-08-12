"""测试 数据清洗。"""
from datetime import datetime

import pytest


class TestDataCleaner:
    def test_clean_rows(self):
        """测试数据清洗。"""
        from backend.data_cleaner import clean_rows
        from backend.schemas import ColumnMeta, ColumnType

        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER, nullable=False),
            ColumnMeta(name="name", dtype=ColumnType.STRING, nullable=True),
            ColumnMeta(name="age", dtype=ColumnType.INTEGER, nullable=True),
        ]
        records = clean_rows(
            [
                {"id": "1", "name": "张三", "age": "18"},
                {"id": "2", "name": "李四", "age": "19"},
                {"id": "3", "name": "王五", "age": "20"},
            ],
            columns,
        )
        assert records == [
            {"id": 1, "name": "张三", "age": 18},
            {"id": 2, "name": "李四", "age": 19},
            {"id": 3, "name": "王五", "age": 20},
        ]
    def test_clean_rows_with_datetime(self):
        """测试数据清洗。"""
        from backend.data_cleaner import clean_rows
        from backend.schemas import ColumnMeta, ColumnType
        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER, nullable=False),
            ColumnMeta(name="name", dtype=ColumnType.STRING, nullable=True),
            ColumnMeta(name="age", dtype=ColumnType.INTEGER, nullable=True),
            ColumnMeta(name="birthday", dtype=ColumnType.DATETIME, nullable=True),
        ]
        records = clean_rows(
            [
                {"id": "1", "name": "张三", "age": "18", "birthday": "2020-01-01"},
                {"id": "2", "name": "李四", "age": "19", "birthday": "2020-01-02"},
                {"id": "3", "name": "王五", "age": "20", "birthday": "2020-01-03"},
            ],columns
        )
        assert records == [
            {"id": 1, "name": "张三", "age": 18, "birthday": datetime(2020, 1, 1)},
            {"id": 2, "name": "李四", "age": 19, "birthday": datetime(2020, 1, 2)},
            {"id": 3, "name": "王五", "age": 20, "birthday": datetime(2020, 1, 3)},
        ]

    def test_clean_rows_with_bool(self):
        """测试数据清洗。"""
        from backend.data_cleaner import clean_rows
        from backend.schemas import ColumnMeta, ColumnType
        columns = [
            ColumnMeta(name="id", dtype=ColumnType.INTEGER, nullable=False),
            ColumnMeta(name="name", dtype=ColumnType.STRING, nullable=True),
            ColumnMeta(name="age", dtype=ColumnType.INTEGER, nullable=True),
            ColumnMeta(name="is_married", dtype=ColumnType.BOOLEAN, nullable=True),
        ]
        records = clean_rows(
            [
                {"id": "1", "name": "张三", "age": "18", "is_married": "true"},
                {"id": "2", "name": "李四", "age": "19", "is_married": "false"},
                {"id": "3", "name": "王五", "age": "20", "is_married": "1"},
                {"id": "4", "name": "王六", "age": "21", "is_married": None},
            ],columns
        )
        assert records == [
            {"id": 1, "name": "张三", "age": 18, "is_married": 1},
            {"id": 2, "name": "李四", "age": 19, "is_married": 0},
            {"id": 3, "name": "王五", "age": 20, "is_married": 1},
            {"id": 4, "name": "王六", "age": 21, "is_married": 0},
        ]
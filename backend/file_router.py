# backend/file_router.py

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import uuid
from backend.parsers.excel_parser import ExcelParser
from backend.data_cleaner import clean_rows
from backend.db import DBManager
from backend.sql_guard import SQLGuard
from backend.agents.nl2sql_agent import NL2SQLAgent
from backend.schemas import ParseResult, ColumnMeta


# ============================================================
# 1. 数据容器 —— 一个会话捆在一起的上下文
# ============================================================

@dataclass
class SessionContext:
    """一个会话的完整上下文。"""
    db: DBManager
    guard: SQLGuard
    agent: NL2SQLAgent
    tables: dict[str, list[ColumnMeta]] = field(default_factory=dict)


# ============================================================
# 2. 模块级变量和函数 —— 操作 _sessions 的工具箱
# ============================================================

_sessions: dict[str, SessionContext] = {}
_seen_files: dict[str, set[str]] = {}

def _new_session() -> tuple[str, SessionContext]:
    """创建新会话，返回 (session_id, context)。"""
    sid = uuid.uuid4().hex[:12]
    ctx = SessionContext(
        db=DBManager(),
        guard=SQLGuard(),
        agent=NL2SQLAgent(),
    )
    _sessions[sid] = ctx
    return sid, ctx


def get_session(session_id: str) -> SessionContext | None:
    """获取已有会话，不存在返回 None。"""
    return _sessions.get(session_id)

def route(file_path: str | Path, session_id: str | None = None) -> tuple[ParseResult, str]:
    """主入口：解析文件 → 清洗 → 建表 → 注册 guard。
    
    Returns:
        (ParseResult, session_id)
    """
    file_path = Path(file_path)         
    # 1. 会话：没有就新建
    if session_id and session_id in _sessions:
        ctx = _sessions[session_id]
    else:
        session_id, ctx = _new_session()
# 2. 根据扩展名分派解析器
    suffix = file_path.suffix.lower()
    if suffix in ('.xlsx', '.xls', '.csv'):
        result = ExcelParser.parse(file_path)
    elif suffix == '.pdf':
        raise ValueError("PDF 解析暂未实现（v2 支持）")
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")
    # 去重：同一会话同一文件只解析一次
    file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
    if session_id not in _seen_files:
        _seen_files[session_id] = set()
    if file_hash in _seen_files[session_id]:
        raise ValueError("该文件已上传过，不能重复上传")

    _seen_files[session_id].add(file_hash)   
    
    # 3. 每个 sheet → 清洗 → 建表 → 入库 → 注册
    for sheet in result.sheets:
        idx = len(ctx.tables)           # 0, 1, 2... 自动递增
        table_name = f"qa_{session_id}_{idx}"    # 表名前缀做隔离
        
        clean_rows(sheet.records, sheet.columns)        # 清洗
        ctx.db.create_table(table_name, sheet.columns)   # 建表
        ctx.db.insert_rows(table_name, sheet.records)    # 入库
        ctx.guard.register_table(table_name)             # 注册白名单
        ctx.tables[table_name] = sheet.columns           # 记录结构
    
    return result, session_id

def build_schema(session_id: str) -> str:
    if session_id not in _sessions:
        raise ValueError("会话不存在")
    ctx = _sessions[session_id]
    schema = ''
    for table_name, columns in ctx.tables.items():
        schema += f"表 {table_name}：\n"
        for column in columns:
            schema += f"{column.name}: {column.dtype.value}\n"
        schema += "\n"
    return schema
       
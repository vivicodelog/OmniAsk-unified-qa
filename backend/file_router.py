# backend/file_router.py

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
from typing import Callable
import uuid
from backend.agents.vision_agent import VisionAgent
from backend.parsers.excel_parser import ExcelParser
from backend.data_cleaner import clean_rows
from backend.db import DBManager
from backend.parsers.pdf_parser import PdfParser
from backend.retrieval.fusion import FusionAgent, build_tools
from backend.retrieval.text_retriever import TextRetriever
from backend.sql_guard import SQLGuard
from backend.agents.nl2sql_agent import NL2SQLAgent
from backend.schemas import ParseResult, ColumnMeta, PdfParseResult


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
    text_retriever: TextRetriever | None = None      # 懒加载：首个 PDF 时才建（下载模型）
    pdfs: dict[str, PdfParseResult] = field(default_factory=dict)   # file_name → 解析结果
    fusion: FusionAgent | None = None                # 有 PDF 时才组装
    vision: VisionAgent | None = None
    file_path: Path | None = None                    # 原始文件路径，供前端 PDF 预览接口取字节流
    sources: list[dict] = field(default_factory=list)  # 溯源：最近一次提问命中的文本块坐标，给前端高亮


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

def route(file_path: str | Path, session_id: str | None = None) -> tuple[ParseResult | PdfParseResult, str]:
    """主入口：按扩展名分派 → 去重 → Excel 建表 / PDF 建索引+组装 fusion。"""
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
        result = PdfParser.parse(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")
    # 去重：同一会话同一文件只解析一次
    file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
    if session_id not in _seen_files:
        _seen_files[session_id] = set()
    if file_hash in _seen_files[session_id]:
        raise ValueError("该文件已上传过，不能重复上传")

    _seen_files[session_id].add(file_hash)   
    if isinstance(result, PdfParseResult):
        # PDF：建索引 + 存 pdfs + 组装 fusion
        if ctx.text_retriever is None:
            ctx.text_retriever = TextRetriever()          # 懒加载：首个 PDF 才下载模型
        ctx.text_retriever.index(result.text_blocks, source=result.file_name)
        ctx.pdfs[result.file_name] = result
        ctx.file_path = file_path.resolve()          # 存绝对路径，前端预览 PDF 时按此取字节流
        ctx.fusion = FusionAgent(
            _build_executors(ctx),
            tools=build_tools(has_tables=bool(ctx.tables), has_pdfs=bool(ctx.pdfs)),
        )   # 组装调度中枢（工具菜单按当前资源裁剪）
    else:
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

def build_manifest(ctx: SessionContext) -> str:
    """拼监督者的资源清单：只列「有什么资源 + 来源标识」，内容留给工具取。"""
    lines: list[str] = ["当前已加载的资源："]

    if ctx.tables:
        lines.append("【表格】")
        for table_name, columns in ctx.tables.items():
            col_desc = "、".join(f"{c.name}({c.dtype.value})" for c in columns)
            lines.append(f"- {table_name}：{col_desc}")

    if ctx.pdfs:
        lines.append("【PDF 文本】")
        for file_name, pdf in ctx.pdfs.items():
            lines.append(f"- {file_name}：已索引 {len(pdf.text_blocks)} 个文本块（第 1-{pdf.page_count} 页）")

        lines.append("【PDF 图片】")
        for file_name, pdf in ctx.pdfs.items():
            for image in pdf.images:
                lines.append(f"- {file_name}：第 {image.page} 页有一张图")

    return "\n".join(lines)

def _build_executors(ctx: SessionContext) -> dict[str, Callable[[dict], str]]:
    # ① 文本检索：source 原样透传
    def search_text(args: dict) -> str:
        if not ctx.text_retriever:
            ctx.text_retriever = TextRetriever()
        hits = ctx.text_retriever.search(args["query"], args["source"])
        # 旁路收集：坐标（page+bbox）给前端高亮，文本照旧拼字符串给 LLM
        ctx.sources.extend(
            {"page": h["page"], "bbox": list(h["bbox"]), "text": h["text"]}
            for h in hits
        )
        return "\n".join(f"[第{h['page']}页] {h['text']}" for h in hits)

    # ② 数据查询：table → 拼该表 schema → 调 NL2SQLAgent
    def sql_query(args: dict) -> str:
        columns = ctx.tables.get(args["table"])
        if columns is None:                      # LLM 可能编造表名，降级不崩
            available = "、".join(ctx.tables) or "（当前没有加载任何表格）"
            return f"表 {args['table']} 不存在。当前可用表格：{available}"
        schema = f"表 {args['table']}：\n" + "\n".join(f"{c.name}: {c.dtype.value}" for c in columns)
        result = ctx.agent.run(args["question"], schema, ctx.db, ctx.guard)
        if result["success"]:
            return f"SQL: {result['sql']}\n结果: {result['data']}"
        if result.get("need_clarify"):
            return result["question"]
        return result.get("error", "查询失败")
    
    # ③ 看图：source + page → 筛出该页的图 → 喂 VisionAgent
    def answer_image(args: dict) -> str:
        pdf = ctx.pdfs.get(args["source"])
        if pdf is None:                          # LLM 可能编造 source，降级不崩
            return f"来源 {args['source']} 不存在"
        images = [img for img in pdf.images if img.page == args["page"]]
        if not ctx.vision:
            ctx.vision = VisionAgent()
        if not images:
            return "该页没有图片"
        return ctx.vision.run(args["question"], images)

    return {"search_text": search_text, "sql_query": sql_query, "answer_image": answer_image}

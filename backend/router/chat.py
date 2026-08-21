# backend/router/chat.py

from fastapi import APIRouter

from backend.file_router import build_manifest, build_schema, get_session
from backend.schemas import ChatRequest, ColumnMeta
from backend.chart_selector import select
from backend.util.infer_dtype import infer_dtype
router = APIRouter()                      

@router.post("/chat")
async def chat(request: ChatRequest):
    ctx = get_session(request.session_id)
    if not ctx:
        return {"answer_type": "error", "error": "会话不存在"}
    # 分流：有 PDF 走 fusion 多模态调度（fusion 里的 sql_query 也能查表），否则走 v1
    if ctx.pdfs:
        manifest = build_manifest(ctx)
        assert ctx.fusion is not None   # pdfs 非空 ⟹ route 里必然已组装 fusion
        ctx.sources.clear()             # 清空上次提问的溯源，本次重新收集（避免跨问题累加）
        answer = ctx.fusion.run(request.question, manifest)
        return {"answer": answer, "answer_type": "text", "sources": ctx.sources}
    schema = build_schema(request.session_id)
    result = ctx.agent.run(request.question, schema, ctx.db, ctx.guard)
    if not result["success"]:
        if result.get("need_clarify"):
            return {"answer_type": "clarify", "question": result["question"]}
        return {"answer_type": "error", "error": result.get("error", "SQL生成失败")}
    columns = []
    if result["data"]:
        keys = result["data"][0].keys()
        for key in keys:
            samples = [row[key] for row in result["data"]]
            columns.append(ColumnMeta(name=key, dtype=infer_dtype(samples)))
    chart_type = select(request.question, columns, result["sql"])
    return {
        "sql": result["sql"],
        "data": result["data"],
        "chart_type": chart_type,
        "answer_type": "chart",
    }
    
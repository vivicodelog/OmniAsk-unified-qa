# backend/router/chat.py

from fastapi import APIRouter

from backend.file_router import build_schema, get_session
from backend.schemas import ChatRequest, ColumnMeta
from backend.chart_selector import select
from backend.util.infer_dtype import infer_dtype
router = APIRouter()                      

@router.post("/chat")
async def chat(request: ChatRequest):
    ctx = get_session(request.session_id)
    if not ctx:                          
        return {"error": "会话不存在"}
    schema = build_schema(request.session_id)
    result = ctx.agent.run(request.question, schema, ctx.db, ctx.guard)
    if not result["success"]:
        return {"error": result.get("error", "SQL生成失败")}
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
    }
    
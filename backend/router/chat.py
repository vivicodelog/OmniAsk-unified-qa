# backend/router/chat.py

from fastapi import APIRouter

from backend.file_router import build_schema, get_session
from backend.schemas import ChatRequest
from backend.chart_selector import select
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
    all_columns = []
    for columns in ctx.tables.values():  # 获取所有表的结构
        all_columns.extend(columns)
    chart_type = select(request.question, all_columns)
    return {
        "sql": result["sql"],
        "data": result["data"],
        "chart_type": chart_type,
    }
    
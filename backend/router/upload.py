# backend/router/upload.py

import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File
from backend.file_router import route as route_file

router = APIRouter()                                   
UPLOAD_DIR = Path("data/uploads")

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 1. 保存文件到本地
    if file.filename is None: return {"error": "No file"}
    ext = Path(file.filename).suffix                     # 取扩展名，如 ".xlsx"
    save_path = UPLOAD_DIR / (uuid.uuid4().hex + ext) # 随机文件名防冲突（组成一个文件名）
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True) # 如果父目录也不存在，一并创建
    content = await file.read()
    save_path.write_bytes(content)

    # 2. 解析 + 建表
    result, session_id = route_file(str(save_path))

    # 3. 返回
    return {
        "session_id": session_id,
        "file_type": result.file_type,
        "sheets": [
            {
                "name": s.name,
                "columns": [c.name for c in s.columns],
                "row_count": s.row_count,
                "data": s.records[:100],  # 前100行用于前端预览
            }
            for s in result.sheets
        ],
    }

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import missing_secrets
from backend.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动即体检：缺密钥时早说，别等用户传完文件才蹦 401
    missing = missing_secrets()
    if missing:
        print(f"[WARN] 未配置的敏感项：{', '.join(missing)}")
        print("       复制 .env.example 为 .env 并填写，否则相关功能调用时会失败")
    yield


app = FastAPI(title="Unified QA", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 开发阶段全放行
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"msg": "Unified QA API"}

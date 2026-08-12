from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.router import router

app = FastAPI(title="Unified QA", version="0.1.0")

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
